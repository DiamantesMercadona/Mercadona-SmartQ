function getVideoMimeType() {
  const preferredTypes = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm']
  return preferredTypes.find((type) => window.MediaRecorder?.isTypeSupported?.(type)) || ''
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function createVideoRecorder(renderer, { fps = 30, filenamePrefix = 'render' } = {}) {
  let mediaRecorder = null
  let recordedChunks = []
  let elapsedTimer = null
  let elapsedSeconds = 0

  const stopElapsedTimer = () => {
    if (elapsedTimer) {
      clearInterval(elapsedTimer)
      elapsedTimer = null
    }
  }

  const startElapsedTimer = (onTick) => {
    elapsedSeconds = 0
    onTick?.(elapsedSeconds)
    stopElapsedTimer()
    elapsedTimer = setInterval(() => {
      elapsedSeconds += 1
      onTick?.(elapsedSeconds)
    }, 1000)
  }

  function start({ onTick, onStart, onStop } = {}) {
    if (!renderer || mediaRecorder) return false
    if (!renderer.domElement?.captureStream) {
      console.warn('Este navegador no soporta captureStream en canvas')
      return false
    }

    try {
      const stream = renderer.domElement.captureStream(fps)
      recordedChunks = []
      const mimeType = getVideoMimeType()
      mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          recordedChunks.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        stopElapsedTimer()
        const blob = new Blob(recordedChunks, {
          type: mediaRecorder?.mimeType || 'video/webm',
        })
        downloadBlob(blob, `${filenamePrefix}-${Date.now()}.webm`)
        recordedChunks = []
        mediaRecorder = null
        onStop?.()
      }

      mediaRecorder.start()
      startElapsedTimer(onTick)
      onStart?.()
      return true
    } catch (error) {
      console.error('No se pudo iniciar la grabación de video:', error)
      stopElapsedTimer()
      mediaRecorder = null
      recordedChunks = []
      return false
    }
  }

  function stop() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      stopElapsedTimer()
      mediaRecorder.stop()
    }
  }

  function dispose() {
    stop()
    stopElapsedTimer()
    recordedChunks = []
    mediaRecorder = null
  }

  return {
    start,
    stop,
    dispose,
  }
}
