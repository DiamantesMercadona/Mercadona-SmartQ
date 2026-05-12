const URL = 'ws://localhost:8000/ws'

class FrameStreamer {
  constructor() {
    this.wsUrl = URL
    this.socket = null
    this.isStreaming = false
    this.streamInterval = null
    this.renderer = null
    this.fps = 30
  }

  // Conecta con el servidor WebSocket
  connect() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      console.log('WebSocket ya está conectado')
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(this.wsUrl)
        this.socket.binaryType = 'arraybuffer'

        this.socket.onopen = () => {
          console.log('Conectado al servidor WebSocket')
          resolve()
        }

        this.socket.onerror = (error) => {
          console.error('Error en WebSocket:', error)
          reject(error)
        }

        this.socket.onclose = () => {
          console.log('Desconectado del servidor WebSocket')
        }
      } catch (error) {
        console.error('Error al crear WebSocket:', error)
        reject(error)
      }
    })
  }

  // Desconecta del servidor WebSocket
  disconnect() {
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }

  // Envía un frame al servidor
  streamFrame() {
    if (!this.renderer || !this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return
    }

    this.renderer.domElement.toBlob(
      (blob) => {
        blob.arrayBuffer().then((buffer) => {
          if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(buffer)
          }
        })
      },
      'image/jpeg',
      0.5, // Baja calidad para ganar velocidad
    )
  }

  // Inicia el streaming de frames. renderer: THREE.WebGLRenderer, fps: number (default: 30)
  async startStreaming(renderer, fps = 30) {
    if (this.isStreaming) {
      console.warn('El streaming ya está activo')
      return
    }

    this.renderer = renderer
    this.fps = fps

    try {
      await this.connect()
      this.isStreaming = true
      const frameInterval = 1000 / this.fps
      this.streamInterval = setInterval(() => this.streamFrame(), frameInterval)
      console.log(`Streaming iniciado a ${this.fps} FPS`)
    } catch (error) {
      console.error('Error al iniciar streaming:', error)
      this.isStreaming = false
    }
  }

  // Detiene el streaming de frames
  stopStreaming() {
    if (!this.isStreaming) {
      console.warn('El streaming no está activo')
      return
    }

    if (this.streamInterval) {
      clearInterval(this.streamInterval)
      this.streamInterval = null
    }

    this.isStreaming = false
    console.log('Streaming detenido')
  }

  // Verifica si el streaming está activo
  isActive() {
    return this.isStreaming
  }
}

export default FrameStreamer
