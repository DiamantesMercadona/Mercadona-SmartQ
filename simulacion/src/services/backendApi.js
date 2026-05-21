/**
 * Capa de acceso al backend usando axios.
 *
 * Exporta funciones HTTP para cada endpoint REST.
 * Exporta `SimulacionWS` (clase) y `simulacionWS` (singleton) para enviar el estado de la simulación al backend vía WebSocket (/ws/video).
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
 * Uso:
 *   import { simulacionWS } from '@/services/backendApi.js'
 *
 *   simulacionWS.onStatusChange = (s) => console.log('WS:', s)
 *   simulacionWS.onAck          = (msg) => console.log('ACK:', msg)
 *   await simulacionWS.connect()
 *   simulacionWS.startSync(miSimulacion, 1000) // enviar cada segundo
 *   simulacionWS.disconnect()
 */
export class SimulacionWS {
  /** @type {'idle'|'connecting'|'connected'|'error'|'disconnected'} */
  status = 'idle'

  #socket = null
  #syncInterval = null

  /** Llamado cuando cambia el estado de la conexión WS. */
  onStatusChange = null

  /** Llamado cuando llega un ACK/mensaje del backend. */
  onAck = null

  /** True si el socket está abierto y listo para enviar. */
  get isConnected() {
    return this.#socket?.readyState === WebSocket.OPEN
  }

  // conexión

  /** Abre la conexión WebSocket con el backend. */
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
        this.stopSync()
        this.#setStatus('disconnected')
      }

      ws.onmessage = ({ data }) => {
        if (!this.onAck) return
        const text = data instanceof ArrayBuffer ? new TextDecoder().decode(data) : String(data)
        this.onAck(text)
      }
    })
  }

  /** Cierra la conexión y detiene la sincronización. */
  disconnect() {
    this.stopSync()
    this.#socket?.close()
    this.#socket = null
  }

  // envío

  /**
   * Envía el estado actual de la simulación por WebSocket (JSON-UTF8).
   * @param {import('../models/Simulacion.js').default} simulacion
   * @returns {boolean} true si el envío fue exitoso
   */
  sendState(simulacion) {
    if (!this.isConnected) return false

    const payload = {
      source: 'simulador-3d',
      timestamp: new Date().toISOString(),
      cajas: simulacion.cajas.map((c) => ({
        id: c.id,
        abierta: c.abierta,
        cola: c.cola.length,
      })),
    }

    this.#socket.send(new TextEncoder().encode(JSON.stringify(payload)))
    return true
  }

  /**
   * Inicia el envío periódico del estado de la simulación.
   * @param {import('../models/Simulacion.js').default} simulacion
   * @param {number} intervalMs – Intervalo en milisegundos (defecto: 1 000)
   */
  startSync(simulacion, intervalMs = 1000) {
    this.stopSync()
    this.#syncInterval = setInterval(() => this.sendState(simulacion), intervalMs)
  }

  /** Pausa el envío periódico sin cerrar la conexión WS. */
  stopSync() {
    if (this.#syncInterval) {
      clearInterval(this.#syncInterval)
      this.#syncInterval = null
    }
  }

  //  privado

  #setStatus(s) {
    this.status = s
    this.onStatusChange?.(s)
  }
}

/** Instancia singleton lista para usar en cualquier componente. */
export const simulacionWS = new SimulacionWS()

/**
 * VideoWS
 *
 * Conecta a /ws/video y envía frames JPEG binarios extraídos de un <canvas>.
 * Pensado para hacer streaming del render 3D (o cualquier canvas) al backend.
 *
 * Uso:
 *   import { videoWS } from '@/services/backendApi.js'
 *
 *   videoWS.onStatusChange = (s) => console.log('VideoWS:', s)
 *   await videoWS.connect()
 *   videoWS.startStreaming(canvasElement, 10)  // 10 FPS
 *   videoWS.stopStreaming()
 *   videoWS.disconnect()
 */
export class VideoWS {
  /** @type {'idle'|'connecting'|'connected'|'error'|'disconnected'} */
  status = 'idle'

  #socket = null
  #streamInterval = null

  /** Llamado cuando cambia el estado de la conexión WS. */
  onStatusChange = null

  get isConnected() {
    return this.#socket?.readyState === WebSocket.OPEN
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
  }

  /**
   * Captura el canvas como JPEG y lo envía por WebSocket.
   * Compatible con HTMLCanvasElement o cualquier objeto con .domElement (THREE.WebGLRenderer).
   * @param {HTMLCanvasElement|{domElement: HTMLCanvasElement}} canvasOrRenderer
   */
  sendFrame(canvasOrRenderer) {
    if (!this.isConnected) return
    const canvas = canvasOrRenderer?.domElement ?? canvasOrRenderer
    canvas.toBlob(
      (blob) => {
        if (!blob || !this.isConnected) return
        blob.arrayBuffer().then((buffer) => {
          if (this.isConnected) this.#socket.send(buffer)
        })
      },
      'image/jpeg',
      0.5,
    )
  }

  /**
   * Inicia el envío periódico de frames.
   * @param {HTMLCanvasElement|{domElement: HTMLCanvasElement}} canvasOrRenderer
   * @param {number} fps - Fotogramas por segundo (defecto: 10)
   */
  startStreaming(canvasOrRenderer, fps = 10) {
    this.stopStreaming()
    const ms = 1000 / fps
    this.#streamInterval = setInterval(() => this.sendFrame(canvasOrRenderer), ms)
  }

  /** Detiene el envío de frames sin cerrar la conexión. */
  stopStreaming() {
    if (this.#streamInterval) {
      clearInterval(this.#streamInterval)
      this.#streamInterval = null
    }
  }

  #setStatus(s) {
    this.status = s
    this.onStatusChange?.(s)
  }
}

/** Instancia singleton lista para usar en cualquier componente. */
export const videoWS = new VideoWS()
