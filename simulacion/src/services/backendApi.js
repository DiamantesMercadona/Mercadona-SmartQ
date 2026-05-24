/**
 * Capa de acceso al backend usando axios.
 *
 * Configuración desde .env:
 *   VITE_BACKEND_URL   – Origen del backend (vacío = mismo origen, proxy Vite)
 *   VITE_API_PREFIX    – Prefijo de la API (defecto: /api/v1)
 */

import axios from 'axios'

const API_PREFIX = import.meta.env.VITE_API_PREFIX || '/api/v1'

// Instancia axios — baseURL siempre relativa para que el proxy de Vite
// (o el proxy de producción) gestione CORS. VITE_BACKEND_URL solo lo usa
// vite.config.js como destino del proxy, nunca el navegador directamente.
const api = axios.create({
  baseURL: API_PREFIX,
  headers: { 'Content-Type': 'application/json' },
})

// Endpoints GET

/** Obtiene el estado de todas las colas. */
export const getQueues = () => api.get('/queues').then((r) => r.data)

/** Obtiene el estado de una cola por ID. */
export const getQueue = (id) => api.get(`/queues/${id}`).then((r) => r.data)

/** Comprueba la conexión con Redis. */
export const checkHealth = () => api.get('/redis/health').then((r) => r.data)

/**
 * Obtiene el último evento de vídeo almacenado en Redis.
 * Devuelve un ArrayBuffer porque el backend lo sirve como octet-stream.
 */
export const getLatestVideoEvent = () =>
  api.get('/video/events/latest', { responseType: 'arraybuffer' }).then((r) => r.data)

// Endpoints POST

/**
 * Actualiza la longitud y el estado de una cola.
 * @param {string|number} id
 * @param {number} length
 * @param {'activa'|'cerrada'} status
 */
export const updateQueue = (id, length, status) =>
  api.post(`/queues/${id}`, { length, status }).then((r) => r.data)

/**
 * Publica un evento de vídeo (estado de una caja) en Redis vía HTTP.
 * @param {string|number} cajaId
 * @param {number} peopleCount
 * @param {'activa'|'cerrada'} status
 */
export const publishVideoEvent = (cajaId, peopleCount, status = 'activa') =>
  api
    .post('/video/events', {
      camera_id: 'simulador-3d',
      zone: `Caja_${cajaId}`,
      people_count: peopleCount,
      metadata: { status },
    })
    .then((r) => r.data)

// Sync helper - publicación masiva del estado de una Simulacion vía HTTP

/**
 * Publica el estado de todas las cajas de una Simulacion como eventos de vídeo.
 * @param {import('../models/Simulacion.js').default} simulacion
 * @returns {Promise<PromiseSettledResult[]>}
 */
export async function syncSimulacion(simulacion) {
  return Promise.allSettled(
    simulacion.cajas.map((c) =>
      publishVideoEvent(c.id, c.cola.length, c.abierta ? 'activa' : 'cerrada'),
    ),
  )
}

// WebSocket

function buildWsUrl(path) {
  // Los WebSockets se conectan directamente al backend, sin pasar por el proxy
  // de Vite. FastAPI no aplica CORSMiddleware a conexiones WS, por lo que no
  // hay problema de CORS. Usar el proxy de Vite para WS es poco fiable.
  const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
  const wsBase = backendUrl.replace(/^http/, 'ws')
  return `${wsBase}${API_PREFIX}${path}`
}

/**
 * VideoWS
 *
 * Conecta a /ws/video y envía frames JPEG binarios extraídos de un <canvas>.
 * Pensado para hacer streaming del render 3D (o cualquier canvas) al backend.
 *
 * La codificación JPEG se delega a un Web Worker (frameEncoder.worker.js) para
 * no bloquear el hilo principal ni interferir con el loop de render de Three.js.
 *
 * Flujo por frame:
 *   1. rAF loop (main)  → time-gate a fps objetivo
 *   2. createImageBitmap(canvas, { resize })  → async, no bloquea main thread
 *   3. postMessage(imageBitmap) → Worker  (zero-copy transfer)
 *   4. Worker: drawImage + convertToBlob → postMessage(ArrayBuffer)  (zero-copy)
 *   5. Main thread: socket.send(buffer)  (~0 ms de trabajo en main)
 *
 * Uso:
 *   const ws = new VideoWS()
 *   ws.onStatusChange = (s) => console.log('VideoWS:', s)
 *   await ws.connect()
 *   ws.startStreaming(renderer, 24)   // 24 FPS, captura a 960 px de ancho
 *   ws.stopStreaming()
 *   ws.disconnect()
 */
export class VideoWS {
  /** @type {'idle'|'connecting'|'connected'|'error'|'disconnected'} */
  status = 'idle'

  #socket = null
  #rafId = null
  #lastFrameTime = 0

  // Worker para codificación JPEG off-thread
  #worker = null
  // true mientras createImageBitmap está en vuelo
  #capturing = false
  // true mientras el worker está codificando
  #encoding = false
  // Dimensiones de captura (calculadas en startStreaming)
  #captureWidth = 960
  #captureHeight = 540

  /** Llamado cuando cambia el estado de la conexión WS. */
  onStatusChange = null

  get isConnected() {
    return this.#socket?.readyState === WebSocket.OPEN
  }

  /** Instancia (lazy) el worker de codificación. */
  #initWorker() {
    if (this.#worker) return
    this.#worker = new Worker(new URL('../workers/frameEncoder.worker.js', import.meta.url), {
      type: 'module',
    })
    this.#worker.onmessage = ({ data }) => {
      this.#encoding = false
      if (data.buffer && this.isConnected) {
        this.#socket.send(data.buffer)
      }
    }
    this.#worker.onerror = () => {
      this.#encoding = false
    }
  }

  connect() {
    return new Promise((resolve, reject) => {
      if (this.isConnected) {
        resolve()
        return
      }

      this.#setStatus('connecting')
      const ws = new WebSocket(buildWsUrl('/ws/video'))
      ws.binaryType = 'arraybuffer'

      ws.onopen = () => {
        this.#socket = ws
        this.#setStatus('connected')
        resolve()
      }

      ws.onerror = (err) => {
        this.#setStatus('error')
        reject(err)
      }

      ws.onclose = () => {
        this.#socket = null
        this.stopStreaming()
        this.#setStatus('disconnected')
      }
    })
  }

  disconnect() {
    this.stopStreaming()
    this.#socket?.close()
    this.#socket = null
    // El worker se mantiene vivo para poder reutilizarlo en reconexiones
  }

  /**
   * Captura el canvas actual y lo envía al worker para codificarlo.
   * Async pero fire-and-forget: el rAF loop no espera su resolución.
   * Los flags #capturing / #encoding evitan ejecuciones solapadas.
   * @param {HTMLCanvasElement|{domElement: HTMLCanvasElement}} canvasOrRenderer
   */
  async sendFrame(canvasOrRenderer) {
    if (!this.isConnected || this.#capturing || this.#encoding) return
    // Backpressure: descartamos el frame si el socket tiene > 256 KB pendientes
    if (this.#socket.bufferedAmount > 256 * 1024) return

    const srcCanvas = canvasOrRenderer?.domElement ?? canvasOrRenderer

    //  Fase 1: captura asíncrona (sin bloquear main thread) 
    this.#capturing = true
    let imageBitmap
    try {
      // createImageBitmap hace el resize en GPU/compositor, no en CPU.
      // El await libera el main thread mientras espera → Three.js sigue renderizando.
      imageBitmap = await createImageBitmap(srcCanvas, {
        resizeWidth: this.#captureWidth,
        resizeHeight: this.#captureHeight,
        resizeQuality: 'low',
      })
    } catch {
      this.#capturing = false
      return
    }
    this.#capturing = false

    // Comprobar estado de nuevo tras el await (pudo cambiar mientras esperábamos)
    if (!this.isConnected || this.#encoding) {
      imageBitmap.close()
      return
    }

    //  Fase 2: enviar al worker (zero-copy transfer) 
    this.#encoding = true
    this.#worker.postMessage(
      {
        imageBitmap,
        width: this.#captureWidth,
        height: this.#captureHeight,
        quality: 0.7,
      },
      [imageBitmap], // transferir ownership → sin copia de píxeles
    )
  }

  /**
   * Inicia el envío periódico de frames.
   * Usa requestAnimationFrame para sincronizar con el ciclo de render del navegador.
   * La captura se reduce automáticamente a maxCaptureWidth píxeles de ancho
   * manteniendo el aspect ratio del canvas fuente.
   *
   * @param {HTMLCanvasElement|{domElement: HTMLCanvasElement}} canvasOrRenderer
   * @param {number} fps              - FPS objetivo (defecto: 24)
   * @param {number} maxCaptureWidth  - Ancho máximo de captura (defecto: 960)
   */
  startStreaming(canvasOrRenderer, fps = 24, maxCaptureWidth = 960) {
    this.stopStreaming()
    this.#initWorker()

    // Calcular dimensiones de captura respetando el aspect ratio
    const srcCanvas = canvasOrRenderer?.domElement ?? canvasOrRenderer
    const scale = Math.min(1, maxCaptureWidth / (srcCanvas.width || maxCaptureWidth))
    this.#captureWidth = Math.round((srcCanvas.width || maxCaptureWidth) * scale)
    this.#captureHeight = Math.round((srcCanvas.height || 540) * scale)

    const intervalMs = 1000 / fps
    this.#lastFrameTime = 0
    this.#capturing = false
    this.#encoding = false

    const loop = (timestamp) => {
      this.#rafId = requestAnimationFrame(loop)
      // Time-gating: solo iniciamos una captura si ha pasado suficiente tiempo
      if (timestamp - this.#lastFrameTime < intervalMs) return
      this.#lastFrameTime = timestamp
      this.sendFrame(canvasOrRenderer) // async, fire-and-forget
    }

    this.#rafId = requestAnimationFrame(loop)
  }

  /** Detiene el envío de frames sin cerrar la conexión ni destruir el worker. */
  stopStreaming() {
    if (this.#rafId !== null) {
      cancelAnimationFrame(this.#rafId)
      this.#rafId = null
    }
    this.#capturing = false
    this.#encoding = false
  }

  #setStatus(s) {
    this.status = s
    this.onStatusChange?.(s)
  }
}

/** Instancia singleton lista para usar en cualquier componente. */
export const videoWS = new VideoWS()
