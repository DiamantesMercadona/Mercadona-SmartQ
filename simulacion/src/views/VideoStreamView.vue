<template>
  <div class="video-stream-view">
    <h2>Video Stream</h2>

    <!-- Control de cajas -->
    <section class="cajas-section">
      <h3>Control de cajas</h3>
      <button @click="cargarCajas">Refrescar</button>
      <div class="cajas-list">
        <div v-for="caja in cajas" :key="caja.id" class="caja-row">
          <span class="caja-id">Caja {{ caja.id }}</span>
          <span class="estado-dot" :class="caja.estado" :title="caja.estado"></span>
          <span class="estado-label">{{ caja.estado }}</span>
          <button :disabled="caja.estado === 'activa'" @click="setCajaEstado(caja.id, 'activa')">
            Abrir
          </button>
          <button :disabled="caja.estado === 'cerrada'" @click="setCajaEstado(caja.id, 'cerrada')">
            Cerrar
          </button>
        </div>
        <p v-if="cajas.length === 0" class="empty">Sin cajas cargadas</p>
      </div>
    </section>

    <!-- Visor WS -->
    <section class="viewer-section">
      <h3>WS /ws/video/events</h3>
      <p class="description">Visor de frames en tiempo real del simulador</p>
      <div class="viewer-controls">
        <button @click="toggleVideoViewer">
          {{ viewerConnected ? 'Desconectar' : 'Conectar' }}
        </button>
        <span class="ws-dot" :class="viewerStatus"></span>
        <span class="ws-label">{{ viewerStatus }}</span>
        <span class="frames-label">{{ framesLabel }}</span>
      </div>
      <canvas ref="viewerCanvas" class="viewer-canvas" width="640" height="480"></canvas>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getCajas, patchCajaEstado } from '../services/backendApi.js'

// -- Cajas --

const cajas = ref([])

async function cargarCajas() {
  try {
    cajas.value = await getCajas()
  } catch (e) {
    console.error('[GET /cajas]', e)
  }
}

async function setCajaEstado(id, estado) {
  try {
    await patchCajaEstado(id, estado)
    await cargarCajas()
  } catch (e) {
    console.error(`[PATCH /cajas/${id}]`, e)
  }
}

onMounted(cargarCajas)

// -- Video viewer --

const viewerCanvas = ref(null)
const viewerStatus = ref('idle')
const frameCount = ref(0)
const fpsDisplay = ref('0.0')

const viewerConnected = computed(() => viewerStatus.value === 'connected')
const framesLabel = computed(() =>
  viewerConnected.value ? `frame ${frameCount.value}  |  ${fpsDisplay.value} fps` : '',
)

let viewerWs = null
let fpsCount = 0
let lastFpsTs = 0

function connectVideoViewer() {
  const apiPrefix = import.meta.env.VITE_API_PREFIX || '/api/v1'
  let wsUrl
  if (import.meta.env.DEV) {
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    wsUrl = backendUrl.replace(/^http/, 'ws') + apiPrefix + '/ws/video/events'
  } else {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    wsUrl = `${protocol}//${location.host}${apiPrefix}/ws/video/events`
  }

  viewerStatus.value = 'connecting'
  viewerWs = new WebSocket(wsUrl)
  viewerWs.binaryType = 'arraybuffer'

  viewerWs.onopen = () => {
    viewerStatus.value = 'connected'
    frameCount.value = 0
    fpsCount = 0
    lastFpsTs = performance.now()
  }

  viewerWs.onclose = () => {
    viewerWs = null
    viewerStatus.value = 'disconnected'
  }

  viewerWs.onerror = () => {
    viewerStatus.value = 'error'
  }

  viewerWs.onmessage = ({ data }) => {
    frameCount.value++
    fpsCount++

    const now = performance.now()
    if (now - lastFpsTs >= 1000) {
      fpsDisplay.value = (fpsCount / ((now - lastFpsTs) / 1000)).toFixed(1)
      fpsCount = 0
      lastFpsTs = now
    }

    const canvas = viewerCanvas.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    const bytes = new Uint8Array(data)
    if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
      const blob = new Blob([data], { type: 'image/jpeg' })
      const url = URL.createObjectURL(blob)
      const img = new Image()
      img.onload = () => {
        if (img.naturalWidth) canvas.width = img.naturalWidth
        if (img.naturalHeight) canvas.height = img.naturalHeight
        ctx.drawImage(img, 0, 0)
        URL.revokeObjectURL(url)
      }
      img.src = url
    } else {
      try {
        const json = JSON.parse(new TextDecoder().decode(data))
        ctx.fillStyle = '#0d0d0d'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = '#4ade80'
        ctx.font = '12px monospace'
        JSON.stringify(json, null, 2)
          .split('\n')
          .forEach((line, i) => ctx.fillText(line, 14, 22 + i * 16))
      } catch {
        // datos desconocidos, ignorar
      }
    }
  }
}

function disconnectVideoViewer() {
  viewerWs?.close()
  viewerWs = null
  viewerStatus.value = 'disconnected'
}

function toggleVideoViewer() {
  if (viewerWs) disconnectVideoViewer()
  else connectVideoViewer()
}

onUnmounted(disconnectVideoViewer)
</script>

<style scoped src="./VideoStreamView.css"></style>
