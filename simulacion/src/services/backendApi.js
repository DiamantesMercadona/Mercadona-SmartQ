/**
 * Capa de acceso al backend usando axios.
 *
 * Configuración desde .env:
 *   VITE_BACKEND_URL   – Origen del backend (vacío = mismo origen, proxy Vite)
 *   VITE_API_PREFIX    – Prefijo de la API (defecto: /api/v1)
 */

import axios from 'axios'
import { workerSetInterval, workerClearInterval } from '../utils/workerTimer.js'

const API_PREFIX = import.meta.env.VITE_API_PREFIX || '/api/v1'

// Instancia axios — baseURL siempre relativa para que el proxy de Vite
// (o el proxy de producción) gestione CORS. VITE_BACKEND_URL solo lo usa
// vite.config.js como destino del proxy, nunca el navegador directamente.
const api = axios.create({
  baseURL: API_PREFIX,
  headers: { 'Content-Type': 'application/json' },
})

//  REST

/** Obtiene la lista de cajas con su estado actual. */
export const getCajas = () => api.get('/cajas').then((r) => r.data.cajas)

/**
 * Obtiene las colas con estado y longitud actual (número de clientes).
 * La longitud se calcula a partir de la última instantánea registrada en el backend.
 * Usado solo en la inicialización de la simulación para poblar las colas.
 */
export const getQueues = () => api.get('/queues').then((r) => r.data.queues ?? [])

/**
 * Actualiza únicamente el estado de una caja.
 * Usa PATCH /cajas/:id con solo el campo `estado`.
 * @param {string|number} id
 * @param {'activa'|'cerrada'} estado
 */
export const patchCajaEstado = (id, estado) =>
  api.patch(`/cajas/${id}`, { estado }).then((r) => r.data)

//  WebSocket

function buildWsUrl(path) {
  if (import.meta.env.DEV) {
    // En desarrollo, conecta directamente al backend para evitar problemas con el proxy WS de Vite
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    const wsBase = backendUrl.replace(/^http/, 'ws')
    return `${wsBase}${API_PREFIX}${path}`
  }
  // En producción, URL relativa al host actual para que nginx haga el proxy
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${location.host}${API_PREFIX}${path}`
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
  #streamingId = null

  // Worker para codificación JPEG off-thread
  #worker = null
  // true mientras createImageBitmap está en vuelo
  #capturing = false
  // true mientras el worker está codificando
  #encoding = false
  // Dimensiones de captura (calculadas en startStreaming)
  #captureWidth = 960
  #captureHeight = 540
  // true si el canvas debe escalarse antes de enviar (scale < 1)
  #needsResize = false

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
      // Si no hay que escalar, no se pasan opciones de resize para preservar la
      // resolución nativa del canvas (igual que la grabación local).
      const bitmapOptions = this.#needsResize
        ? {
            resizeWidth: this.#captureWidth,
            resizeHeight: this.#captureHeight,
            resizeQuality: 'high',
          }
        : {}
      imageBitmap = await createImageBitmap(srcCanvas, bitmapOptions)
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
        quality: 0.92,
      },
      [imageBitmap], // transferir ownership → sin copia de píxeles
    )
  }

  /**
   * Inicia el envío periódico de frames.
   * Usa un worker timer para no detenerse cuando la ventana pierde el foco.
   * Por defecto se usa la resolución nativa del canvas (sin downscale), igual
   * que en la grabación local. Pasar maxCaptureWidth para limitarla si se
   * necesita reducir el ancho de banda.
   *
   * @param {HTMLCanvasElement|{domElement: HTMLCanvasElement}} canvasOrRenderer
   * @param {number} fps              - FPS objetivo (defecto: 24)
   * @param {number} maxCaptureWidth  - Ancho máximo de captura (defecto: Infinity = resolución nativa)
   */
  startStreaming(canvasOrRenderer, fps = 24, maxCaptureWidth = Infinity) {
    this.stopStreaming()
    this.#initWorker()

    // Calcular dimensiones de captura respetando el aspect ratio.
    // Si maxCaptureWidth >= ancho del canvas, scale = 1 y no se hace resize.
    const srcCanvas = canvasOrRenderer?.domElement ?? canvasOrRenderer
    const scale = Math.min(1, maxCaptureWidth / (srcCanvas.width || maxCaptureWidth))
    this.#captureWidth = Math.round((srcCanvas.width || maxCaptureWidth) * scale)
    this.#captureHeight = Math.round((srcCanvas.height || 540) * scale)
    this.#needsResize = scale < 1

    const intervalMs = 1000 / fps
    this.#capturing = false
    this.#encoding = false

    this.#streamingId = workerSetInterval(() => {
      this.sendFrame(canvasOrRenderer) // async, fire-and-forget
    }, intervalMs)
  }

  /** Detiene el envío de frames sin cerrar la conexión ni destruir el worker. */
  stopStreaming() {
    workerClearInterval(this.#streamingId)
    this.#streamingId = null
    this.#capturing = false
    this.#encoding = false
  }

  #setStatus(s) {
    this.status = s
    this.onStatusChange?.(s)
  }
}
