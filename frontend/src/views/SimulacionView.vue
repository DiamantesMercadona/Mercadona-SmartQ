<template>
  <main class="simulacion-dashboard">
    <header class="dashboard-header">
      <div class="header-left">
        <RouterLink class="back-link" :to="{ name: 'menu' }">
          <span class="back-arrow">←</span> Volver al menú
        </RouterLink>
        <div class="title-container">
          <span class="kicker">SmartQ</span>
          <h1>Monitor de colas</h1>
        </div>
        <p class="subtitle">Monitorización en tiempo real del flujo de clientes y análisis de colas de las cajas</p>
      </div>
      <div class="header-right">
        <button 
          @click="toggleConnection" 
          :class="['btn-connection', wsStatus]"
        >
          <span class="status-indicator-dot"></span>
          {{ isConnected ? 'Desconectar cámara' : 'Conectar cámara' }}
        </button>
      </div>
    </header>

    <!-- Metrics Cards Row -->
    <section class="metrics-row">
      <div class="metric-card">
        <div class="metric-icon">{{ congestionLevel.icon }}</div>
        <div class="metric-details">
          <span class="metric-label">Nivel de congestión</span>
          <span :class="['metric-value', congestionLevel.class]">{{ congestionLevel.text }}</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">🛒</div>
        <div class="metric-details">
          <span class="metric-label">Cajas abiertas</span>
          <span class="metric-value">{{ activeCajasCount }} / 6</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">👥</div>
        <div class="metric-details">
          <span class="metric-label">Clientes en cola</span>
          <span class="metric-value">{{ totalQueueLength }}</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">⏱️</div>
        <div class="metric-details">
          <span class="metric-label">Tiempo medio de espera</span>
          <span class="metric-value">{{ formattedAverageWaitTime }} min</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">🧑‍✈️</div>
        <div class="metric-details">
          <span class="metric-label">Siguiente cajero</span>
          <span class="metric-value" :class="nextEmployeeOnDutyClass">{{ nextEmployeeOnDuty }}</span>
        </div>
      </div>
    </section>

    <!-- Main Content Grid -->
    <section class="main-grid">
      <!-- Video Visualizer -->
      <div class="visualizer-container">
        <div class="visualizer-header">
          <span class="visualizer-title">
            <span class="live-badge" v-if="isConnected">DIRECTO</span>
            Cajas de la salida de calle Roger de Lauria
          </span>
          <span class="visualizer-stats" v-if="isConnected">
            Actualizando en tiempo real | {{ fpsDisplay }} fps
          </span>
        </div>

        <div class="canvas-wrapper">
          <canvas ref="canvasRef" class="video-canvas"></canvas>
          
          <div v-if="!isConnected" class="offline-overlay">
            <div class="offline-logo">🎥</div>
            <h3>Sensor de cámara inactivo</h3>
            <p>Conéctate al flujo de la cámara inteligente para visualizar la segmentación y el análisis del estado de las colas de manera interactiva.</p>
            <button @click="connectWs" class="btn-connect-overlay">Iniciar cámara</button>
          </div>
        </div>
      </div>

      <!-- Checkout Status Sidebar -->
      <div class="sidebar-container">
        <div class="sidebar-header">
          <h2>Estado de las cajas</h2>
          <span class="refresh-indicator" :class="{ refreshing: loadingQueues }"></span>
        </div>

        <div class="checkout-list">
          <div 
            v-for="caja in sortedQueues" 
            :key="caja.id" 
            :class="['checkout-card', caja.status === 'cerrada' ? 'cerrada' : 'activa']"
          >
            <div class="checkout-top">
              <span class="checkout-name">Caja {{ caja.id }}</span>
              <span :class="['status-badge', caja.status === 'cerrada' ? 'cerrada' : 'activa']">
                {{ caja.status !== 'cerrada' ? 'Abierta' : 'Cerrada' }}
              </span>
            </div>
            
            <div class="checkout-body">
              <div v-if="caja.status !== 'cerrada'" class="cashier-info">
                <span class="info-label">Cajero:</span>
                <span class="info-value">{{ getEmpleadoNombre(caja.id_empleado) }}</span>
              </div>
              
              <div v-if="caja.status !== 'cerrada'" class="queue-status-bar">
                <div class="queue-label-row">
                  <span class="info-label">Clientes en cola:</span>
                  <span class="queue-count" :class="{ congested: caja.length >= 5 }">
                    {{ caja.length }}
                  </span>
                </div>
                <div class="progress-track">
                  <div 
                    class="progress-fill" 
                    :style="{ width: `${Math.min(100, (caja.length / 6) * 100)}%` }"
                    :class="{ high: caja.length >= 5, medium: caja.length >= 3 && caja.length < 5 }"
                  ></div>
                </div>
              </div>

              <!-- Controles de Apertura (Cerrada) -->
              <div v-if="caja.status === 'cerrada'" class="control-apertura">
                <label class="dropdown-label">Asignar cajero:</label>
                <select v-model="selectedEmployeeForCaja[caja.id]" class="cashier-select">
                  <option value="" disabled>Seleccionar empleado</option>
                  <option 
                    v-for="emp in availableEmployees" 
                    :key="emp.id" 
                    :value="emp.id"
                  >
                    {{ emp.nombre }}
                  </option>
                </select>
                <button 
                  @click="openCheckout(caja.id)" 
                  class="btn-checkout-action open"
                  :disabled="loadingQueues"
                >
                  Abrir caja
                </button>
              </div>

              <!-- Controles de Cierre (Activa) -->
              <div v-if="caja.status !== 'cerrada'" class="control-cierre">
                <button 
                  @click="closeCheckout(caja.id)" 
                  class="btn-checkout-action close"
                  :disabled="loadingQueues"
                >
                  Cerrar caja
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// Estado colas y empleados
const queues = ref([])
const empleados = ref({})
const loadingQueues = ref(false)
const realAverageWaitSeconds = ref(0.0)

// Cajero seleccionado por caja para la apertura manual
const selectedEmployeeForCaja = ref({})

// WS de Video Procesado
const wsStatus = ref('disconnected')
const frameCount = ref(0)
const fpsDisplay = ref('0.0')
const canvasRef = ref(null)

const isConnected = computed(() => wsStatus.value === 'connected')

const statusLabel = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return 'Activa'
    case 'connecting': return 'Conectando...'
    case 'error': return 'Error de red'
    default: return 'Desconectada'
  }
})

// Métricas agregadas
const sortedQueues = computed(() => {
  return [...queues.value].sort((a, b) => Number(a.id) - Number(b.id))
})

const activeCajasCount = computed(() => {
  return queues.value.filter(q => q.status !== 'cerrada').length
})

const totalQueueLength = computed(() => {
  return queues.value.reduce((sum, q) => sum + (q.status !== 'cerrada' ? q.length : 0), 0)
})

// Obtener empleados libres (no asignados a cajas activas)
const availableEmployees = computed(() => {
  const list = Object.entries(empleados.value).map(([id, nombre]) => ({ id: Number(id), nombre }))
  const occupiedIds = queues.value
    .filter(q => q.status !== 'cerrada' && q.id_empleado)
    .map(q => Number(q.id_empleado))
  return list.filter(emp => !occupiedIds.includes(emp.id))
})

// Obtener el primer nombre del empleado de guardia
const nextEmployeeOnDuty = computed(() => {
  if (availableEmployees.value.length === 0) return 'Sin personal'
  return availableEmployees.value[0].nombre.split(' ')[0]
})

const nextEmployeeOnDutyClass = computed(() => {
  return availableEmployees.value.length > 0 ? 'bajo' : 'disconnected'
})

// Calcular nivel de congestión dinámico basado en las colas y tiempos de espera
const congestionLevel = computed(() => {
  if (queues.value.filter(q => q.status !== 'cerrada').length === 0) {
    return { text: 'Fluido', class: 'bajo', icon: '🟢' }
  }
  const waitMin = realAverageWaitSeconds.value / 60
  if (waitMin < 1.5) {
    return { text: 'Fluido', class: 'bajo', icon: '🟢' }
  } else if (waitMin < 3.0) {
    return { text: 'Moderado', class: 'medio', icon: '🟡' }
  } else {
    return { text: 'Saturado', class: 'alto', icon: '🔴' }
  }
})

// Convertir tiempo medio de espera de la API a formato minutos legible
const formattedAverageWaitTime = computed(() => {
  if (realAverageWaitSeconds.value <= 0) return '0.0'
  return (realAverageWaitSeconds.value / 60).toFixed(1)
})

let ws = null
let fpsCount = 0
let lastFpsTs = 0
let pollInterval = null

// Obtener información de colas
async function fetchQueues() {
  loadingQueues.value = true
  try {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const res = await fetch(`${apiBase}/queues`)
    if (res.ok) {
      const data = await res.json()
      queues.value = data.queues || []
    }
  } catch (e) {
    console.error('Error al obtener colas:', e)
  } finally {
    loadingQueues.value = false
  }
}

// Obtener estadísticas reales (Métricas) en tiempo real
async function fetchRealStats() {
  try {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const res = await fetch(`${apiBase}/metricas?limite=10`)
    if (res.ok) {
      const data = await res.json()
      const list = data.metricas || []
      
      // Filtrar por métricas del procesador de decisiones
      const decisionMetrics = list.filter(m => m.fuente === 'decision_processor')
      
      if (decisionMetrics.length > 0) {
        const sum = decisionMetrics.reduce((acc, m) => acc + m.tiempo_medio_espera_segundos, 0)
        realAverageWaitSeconds.value = sum / decisionMetrics.length
      } else if (list.length > 0) {
        const sum = list.reduce((acc, m) => acc + m.tiempo_medio_espera_segundos, 0)
        realAverageWaitSeconds.value = sum / list.length
      } else {
        // Estimación heurística de respaldo en caso de base de datos vacía
        const rawWait = totalQueueLength.value * 90 // 90 segundos por cliente
        realAverageWaitSeconds.value = activeCajasCount.value > 0 ? (rawWait / activeCajasCount.value) : 0.0
      }
    }
  } catch (e) {
    console.error('Error al obtener estadísticas reales:', e)
  }
}

// Obtener listado de empleados para mapear nombres
async function fetchEmpleados() {
  try {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const res = await fetch(`${apiBase}/empleados`)
    if (res.ok) {
      const data = await res.json()
      const list = data.empleados || []
      const map = {}
      list.forEach(emp => {
        map[emp.id] = `${emp.nombre} ${emp.apellidos}`
      })
      empleados.value = map
    }
  } catch (e) {
    console.error('Error al obtener empleados:', e)
  }
}

function getEmpleadoNombre(idEmpleado) {
  if (!idEmpleado) return 'Sin asignar'
  return empleados.value[idEmpleado] || `Empleado #${idEmpleado}`
}

// Acciones del Operario: Abrir Caja
async function openCheckout(cajaId) {
  const employeeId = selectedEmployeeForCaja.value[cajaId] || null
  loadingQueues.value = true
  try {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const res = await fetch(`${apiBase}/cajas/${cajaId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        estado: 'abierta',
        id_empleado: employeeId ? Number(employeeId) : null
      })
    })
    if (res.ok) {
      await fetchQueues()
      await fetchRealStats()
      selectedEmployeeForCaja.value[cajaId] = ''
    }
  } catch (e) {
    console.error(`Error al abrir caja ${cajaId}:`, e)
  } finally {
    loadingQueues.value = false
  }
}

// Acciones del Operario: Cerrar Caja
async function closeCheckout(cajaId) {
  loadingQueues.value = true
  try {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const res = await fetch(`${apiBase}/cajas/${cajaId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        estado: 'cerrada',
        id_empleado: null
      })
    })
    if (res.ok) {
      await fetchQueues()
      await fetchRealStats()
    }
  } catch (e) {
    console.error(`Error al cerrar caja ${cajaId}:`, e)
  } finally {
    loadingQueues.value = false
  }
}

// Conectar WebSocket
function connectWs() {
  const apiPrefix = import.meta.env.VITE_API_PREFIX || '/api/v1'
  let wsUrl
  if (import.meta.env.DEV) {
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    wsUrl = backendUrl.replace(/^http/, 'ws') + apiPrefix + '/ws/video/processed/events'
  } else {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    wsUrl = `${protocol}//${location.host}${apiPrefix}/ws/video/processed/events`
  }

  wsStatus.value = 'connecting'
  ws = new WebSocket(wsUrl)
  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    wsStatus.value = 'connected'
    frameCount.value = 0
    fpsCount = 0
    lastFpsTs = performance.now()
  }

  ws.onclose = () => {
    ws = null
    if (wsStatus.value !== 'disconnected') {
      wsStatus.value = 'disconnected'
    }
  }

  ws.onerror = () => {
    wsStatus.value = 'error'
  }

  ws.onmessage = ({ data }) => {
    frameCount.value++
    fpsCount++

    const now = performance.now()
    if (now - lastFpsTs >= 1000) {
      fpsDisplay.value = (fpsCount / ((now - lastFpsTs) / 1000)).toFixed(1)
      fpsCount = 0
      lastFpsTs = now
    }

    const canvas = canvasRef.value
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
    }
  }
}

function disconnectWs() {
  if (ws) {
    ws.close()
    ws = null
  }
  wsStatus.value = 'disconnected'
}

function toggleConnection() {
  if (isConnected.value) {
    disconnectWs()
  } else {
    connectWs()
  }
}

onMounted(async () => {
  await fetchEmpleados()
  await fetchQueues()
  await fetchRealStats()
  
  // Conectar automáticamente al cargar
  connectWs()

  // Polling de datos y colas cada 2 segundos
  pollInterval = setInterval(async () => {
    await fetchQueues()
    await fetchRealStats()
  }, 2000)
})

onUnmounted(() => {
  disconnectWs()
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.simulacion-dashboard {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 24px;
  background: 
    radial-gradient(circle at top left, rgba(0, 132, 61, 0.14), transparent 28%),
    linear-gradient(135deg, #f5f8f3 0%, #e9f1ea 48%, #f8faf8 100%); /* Esquema de color exacto Mercadona SmartQ */
  color: #173326;
  font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Header */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  border-bottom: 1px solid rgba(23, 51, 38, 0.12);
  padding-bottom: 16px;
}

.back-link {
  color: #00843d;
  font-weight: 800;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95rem;
  transition: all 0.2s ease;
}

.back-link:hover {
  color: #00662f;
  transform: translateX(-4px);
}

.title-container {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  margin-bottom: 6px;
}

.title-container h1 {
  margin: 0 !important;
}

.kicker {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border: 1px solid rgba(0, 132, 61, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #007d3a;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 6px 0 4px;
  font-size: 2rem;
  font-weight: 800;
  color: #173326;
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.subtitle {
  margin: 0;
  color: #506459;
  font-size: 1rem;
}

/* Botón Conexión */
.btn-connection {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  border-radius: 8px;
  border: 1px solid rgba(23, 51, 38, 0.15);
  background: rgba(255, 255, 255, 0.85);
  color: #173326;
  font-size: 0.9rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(23, 51, 38, 0.05);
}

.status-indicator-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #627267;
  transition: background 0.25s ease;
}

.btn-connection.connected {
  border-color: rgba(0, 132, 61, 0.3);
  background: rgba(0, 132, 61, 0.06);
}
.btn-connection.connected .status-indicator-dot {
  background: #00843d;
  box-shadow: 0 0 8px #00843d;
  animation: pulse-active 1.5s infinite;
}

.btn-connection.connecting {
  border-color: rgba(250, 204, 21, 0.3);
  background: rgba(250, 204, 21, 0.06);
}
.btn-connection.connecting .status-indicator-dot {
  background: #facc15;
  animation: pulse-active 1s infinite;
}

.btn-connection.error {
  border-color: rgba(215, 25, 32, 0.3);
  background: rgba(215, 25, 32, 0.06);
}
.btn-connection.error .status-indicator-dot {
  background: #d71920;
}

.btn-connection:hover {
  transform: translateY(-2px);
  background: #ffffff;
  border-color: rgba(0, 132, 61, 0.35);
  box-shadow: 0 6px 16px rgba(23, 51, 38, 0.08);
}

/* Metrics Row */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.metric-card {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 8px 24px rgba(23, 51, 38, 0.05);
}

.metric-icon {
  font-size: 1.8rem;
  background: rgba(0, 132, 61, 0.08);
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 8px;
}

.metric-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-label {
  font-size: 0.82rem;
  color: #627267;
  font-weight: 700;
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 800;
  color: #173326;
}

.metric-value.connected { color: #00843d; }
.metric-value.connecting { color: #facc15; }
.metric-value.error { color: #d71920; }
.metric-value.disconnected { color: #627267; }
.metric-value.bajo { color: #00843d; }
.metric-value.medio { color: #ca8a04; }
.metric-value.alto { color: #d71920; }

/* Grid principal */
.main-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
  align-items: stretch;
}

@media (max-width: 1024px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
}

/* Video Visualizer */
.visualizer-container {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 32px rgba(23, 51, 38, 0.06);
}

.visualizer-header {
  padding: 12px 18px;
  background: rgba(0, 0, 0, 0.02);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(23, 51, 38, 0.1);
}

.visualizer-title {
  font-weight: 800;
  font-size: 0.95rem;
  color: #173326;
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-badge {
  background: #d71920;
  color: #ffffff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  animation: pulse-active 1.2s infinite;
}

.visualizer-stats {
  font-size: 0.8rem;
  font-weight: 700;
  color: #627267;
}

.canvas-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 1904 / 935;
  background: #f1f5f0;
  display: grid;
  place-items: center;
}

.video-canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.offline-overlay {
  position: absolute;
  inset: 0;
  background: rgba(245, 248, 243, 0.96);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 24px;
}

.offline-logo {
  font-size: 3rem;
  margin-bottom: 12px;
  animation: float 3s ease-in-out infinite;
}

.offline-overlay h3 {
  margin: 0 0 8px;
  font-size: 1.25rem;
  color: #173326;
}

.offline-overlay p {
  margin: 0 0 20px;
  max-width: 440px;
  color: #506459;
  font-size: 0.9rem;
  line-height: 1.5;
}

.btn-connect-overlay {
  padding: 10px 24px;
  border: none;
  background: #00843d;
  color: #ffffff;
  border-radius: 8px;
  font-weight: 800;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(0, 132, 61, 0.2);
}

.btn-connect-overlay:hover {
  background: #009947;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 132, 61, 0.3);
}

/* Sidebar de Cajas */
.sidebar-container {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: 0 12px 32px rgba(23, 51, 38, 0.06);
  height: 100%;
  box-sizing: border-box;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(23, 51, 38, 0.1);
  padding-bottom: 10px;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: #173326;
}

.refresh-indicator {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(23, 51, 38, 0.15);
  border-top-color: #00843d;
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.refresh-indicator.refreshing {
  opacity: 1;
  animation: spin 0.8s linear infinite;
}

.checkout-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.checkout-list::-webkit-scrollbar {
  width: 4px;
}
.checkout-list::-webkit-scrollbar-thumb {
  background: rgba(0, 132, 61, 0.15);
  border-radius: 4px;
}

.checkout-card {
  background: #ffffff;
  border: 1px solid rgba(23, 51, 38, 0.1);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(23, 51, 38, 0.02);
}

.checkout-card:hover {
  border-color: rgba(0, 132, 61, 0.25);
  transform: translateX(2px);
  box-shadow: 0 4px 12px rgba(23, 51, 38, 0.05);
}

.checkout-card.activa {
  border-left: 3px solid #00843d;
}

.checkout-card.cerrada {
  border-left: 3px solid #d71920;
  background: rgba(245, 248, 243, 0.5);
}

.checkout-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.checkout-name {
  font-weight: 800;
  font-size: 1rem;
  color: #173326;
}

.status-badge {
  font-size: 0.7rem;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.status-badge.activa {
  background: rgba(0, 132, 61, 0.08);
  color: #00843d;
  border: 1px solid rgba(0, 132, 61, 0.15);
}

.status-badge.cerrada {
  background: rgba(215, 25, 32, 0.08);
  color: #d71920;
  border: 1px solid rgba(215, 25, 32, 0.15);
}

.checkout-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cashier-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
}

.info-label {
  color: #627267;
  font-weight: 700;
}

.info-value {
  font-weight: 700;
  color: #173326;
}

/* Controles de Caja (Operario) */
.control-apertura, .control-cierre {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px dashed rgba(23, 51, 38, 0.1);
}

.dropdown-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #627267;
}

.cashier-select {
  width: 100%;
  min-height: 36px;
  box-sizing: border-box;
  border: 1px solid rgba(23, 51, 38, 0.18);
  border-radius: 6px;
  padding: 0 10px;
  background: #ffffff;
  color: #173326;
  font-size: 0.85rem;
}

.btn-checkout-action {
  width: 100%;
  min-height: 36px;
  border-radius: 6px;
  font-weight: 800;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.btn-checkout-action.open {
  background: #e6f2ec;
  color: #00843d;
  border: 1px solid rgba(0, 132, 61, 0.25);
}
.btn-checkout-action.open:hover:not(:disabled) {
  background: #d0e8dc;
}

.btn-checkout-action.close {
  background: #fdf2f2;
  color: #d71920;
  border: 1px solid rgba(215, 25, 32, 0.25);
}
.btn-checkout-action.close:hover:not(:disabled) {
  background: #fbe0e0;
}

.btn-checkout-action:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  border-color: rgba(23, 51, 38, 0.1);
}

/* Barra de progreso de cola */
.queue-status-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.queue-label-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
}

.queue-count {
  font-weight: 800;
  color: #00843d;
}

.queue-count.congested {
  color: #d71920;
  animation: pulse-text 1.5s infinite;
}

.progress-track {
  width: 100%;
  height: 6px;
  background: #eef4ed;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  background: #00843d;
  transition: width 0.4s ease;
}

.progress-fill.medium {
  background: #facc15;
}

.progress-fill.high {
  background: #d71920;
}

/* Animaciones */
@keyframes pulse-active {
  0% { opacity: 0.8; box-shadow: 0 0 0 0 rgba(0, 132, 61, 0.4); }
  70% { opacity: 1; box-shadow: 0 0 0 8px rgba(0, 132, 61, 0); }
  100% { opacity: 0.8; box-shadow: 0 0 0 0 rgba(0, 132, 61, 0); }
}

@keyframes pulse-text {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

<style>
/* Quitar el marco blanco alrededor del contenedor del navegador */
html, body {
  margin: 0 !important;
  padding: 0 !important;
  background-color: #f5f8f3;
}
</style>
