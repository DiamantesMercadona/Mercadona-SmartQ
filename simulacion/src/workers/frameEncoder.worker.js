/**
 * Worker para codificación JPEG fuera del hilo principal.
 *
 * Flujo:
 *   Main thread  →  { imageBitmap, width, height, quality }  →  Worker
 *   Worker       →  { buffer: ArrayBuffer }                  →  Main thread  (zero-copy transfer)
 *
 * El ImageBitmap también se transfiere (zero-copy), de forma que nunca se
 * copian los píxeles — solo cambia el "propietario" de la memoria.
 */

let offscreen = null
let ctx = null

self.onmessage = async ({ data }) => {
  const { imageBitmap, width, height, quality } = data

  try {
    // Reutilizar el OffscreenCanvas si las dimensiones no cambian
    if (!offscreen || offscreen.width !== width || offscreen.height !== height) {
      offscreen = new OffscreenCanvas(width, height)
      ctx = offscreen.getContext('2d')
    }

    ctx.drawImage(imageBitmap, 0, 0)
    imageBitmap.close() // liberar memoria en cuanto ya no hace falta

    const blob = await offscreen.convertToBlob({ type: 'image/jpeg', quality })
    const buffer = await blob.arrayBuffer()

    // Transferir el ArrayBuffer al hilo principal sin copiarlo
    self.postMessage({ buffer }, [buffer])
  } catch (err) {
    imageBitmap?.close()
    self.postMessage({ error: String(err) })
  }
}
