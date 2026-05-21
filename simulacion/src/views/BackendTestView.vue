<template>
  <div class="test-view">
    <h2>Backend Test</h2>

    <!-- GET /queues -->
    <section>
      <h3>GET /queues</h3>
      <p class="description">Obtiene todas las colas del sistema</p>
      <button @click="testGetQueues">Ejecutar</button>
    </section>

    <!-- GET /queues/:id -->
    <section>
      <h3>GET /queues/:id</h3>
      <p class="description">Obtiene el estado de una cola por ID</p>
      <label>
        ID de cola
        <input v-model.number="queueId" type="number" min="1" placeholder="1" />
      </label>
      <button @click="testGetQueue">Ejecutar</button>
    </section>

    <!-- POST /queues/:id -->
    <section>
      <h3>POST /queues/:id</h3>
      <p class="description">Actualiza la longitud y estado de una cola</p>
      <label>
        ID de cola
        <input v-model.number="updateId" type="number" min="1" placeholder="1" />
      </label>
      <label>
        Longitud
        <input v-model.number="updateLength" type="number" min="0" placeholder="0" />
      </label>
      <label>
        Estado
        <select v-model="updateStatus">
          <option value="activa">activa</option>
          <option value="cerrada">cerrada</option>
        </select>
      </label>
      <button @click="testUpdateQueue">Ejecutar</button>
    </section>

    <!-- POST /video/events -->
    <section>
      <h3>POST /video/events</h3>
      <p class="description">Publica un evento de video con el estado de una caja</p>
      <label>
        ID de caja
        <input v-model.number="eventCajaId" type="number" min="1" placeholder="1" />
      </label>
      <label>
        Personas en cola
        <input v-model.number="eventPeople" type="number" min="0" placeholder="0" />
      </label>
      <label>
        Estado
        <select v-model="eventStatus">
          <option value="activa">activa</option>
          <option value="cerrada">cerrada</option>
        </select>
      </label>
      <button @click="testVideoEvent">Ejecutar</button>
    </section>

    <!-- GET /video/events/latest -->
    <section>
      <h3>GET /video/events/latest</h3>
      <p class="description">Obtiene el ultimo evento de video almacenado en Redis</p>
      <button @click="testGetLatestVideo">Ejecutar</button>
    </section>

    <!-- GET /redis/health -->
    <section>
      <h3>GET /redis/health</h3>
      <p class="description">Comprueba la conexion con Redis</p>
      <button @click="testHealth">Ejecutar</button>
    </section>

    <!-- WS /ws/video/events -->
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
import { ref, computed, onUnmounted } from 'vue'
import {
  getQueues,
  getQueue,
  updateQueue,
  publishVideoEvent,
  checkHealth,
  getLatestVideoEvent,
} from '../services/backendApi.js'

const queueId = ref(1)
const updateId = ref(1)
const updateLength = ref(0)
const updateStatus = ref('activa')
const eventCajaId = ref(1)
const eventPeople = ref(0)
const eventStatus = ref('activa')

// Video viewer
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
  const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
  const wsUrl = backendUrl.replace(/^http/, 'ws') + apiPrefix + '/ws/video/events'

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

async function testGetQueues() {
  try {
    console.log('[GET /queues]', await getQueues())
  } catch (e) {
    console.error('[GET /queues]', e)
  }
}

async function testGetQueue() {
  try {
    console.log(`[GET /queues/${queueId.value}]`, await getQueue(queueId.value))
  } catch (e) {
    console.error(`[GET /queues/${queueId.value}]`, e)
  }
}

async function testUpdateQueue() {
  try {
    console.log(
      `[POST /queues/${updateId.value}]`,
      await updateQueue(updateId.value, updateLength.value, updateStatus.value),
    )
  } catch (e) {
    console.error(`[POST /queues/${updateId.value}]`, e)
  }
}

async function testVideoEvent() {
  try {
    console.log(
      '[POST /video/events]',
      await publishVideoEvent(eventCajaId.value, eventPeople.value, eventStatus.value),
    )
  } catch (e) {
    console.error('[POST /video/events]', e)
  }
}

async function testGetLatestVideo() {
  try {
    const data = await getLatestVideoEvent()
    const text = new TextDecoder().decode(data)
    console.log('[GET /video/events/latest]', JSON.parse(text))
  } catch (e) {
    console.error('[GET /video/events/latest]', e)
  }
}

async function testHealth() {
  try {
    console.log('[GET /redis/health]', await checkHealth())
  } catch (e) {
    console.error('[GET /redis/health]', e)
  }
}
</script>

<style scoped>
.test-view {
  padding: 24px;
  font-family: monospace;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

h2 {
  margin: 0;
}

section {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

h3 {
  margin: 0;
  width: 100%;
  font-size: 13px;
  color: #888;
}

.description {
  margin: 0;
  width: 100%;
  font-size: 12px;
  color: #555;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: #aaa;
}

input,
select {
  padding: 4px 8px;
  border: 1px solid #444;
  border-radius: 4px;
  background: #1e1e1e;
  color: #eee;
  font-size: 13px;
  width: 100px;
}

button {
  padding: 4px 14px;
  border: 1px solid #555;
  border-radius: 4px;
  background: #2d2d2d;
  color: #eee;
  cursor: pointer;
  font-size: 13px;
  align-self: flex-end;
}

button:hover {
  background: #3d3d3d;
}

.viewer-section {
  flex-direction: column;
  align-items: flex-start;
}

.viewer-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4b5563;
  transition: background 0.3s;
  flex-shrink: 0;
}

.ws-dot.connected {
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.7);
}

.ws-dot.error {
  background: #ef4444;
}

.ws-dot.disconnected {
  background: #6b7280;
}

.ws-label {
  font-size: 12px;
  color: #aaa;
}

.frames-label {
  font-size: 11px;
  color: #555;
}

.viewer-canvas {
  border: 1px solid #1f2937;
  border-radius: 6px;
  max-width: 100%;
  margin-top: 10px;
}
</style>
