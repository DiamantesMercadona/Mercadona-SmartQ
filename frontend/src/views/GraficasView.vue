<script setup>
import { computed, onMounted, ref } from 'vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const metrics = ref([])
const loading = ref(false)
const errorMessage = ref('')
const selectedBox = ref('todas')
const selectedLimit = ref(100)

const endpointCandidates = ['/metricas', '/metrics']

const requestJson = async (path) => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Error HTTP ${response.status}`)
  }

  return response.json()
}

const normalizeMetric = (metric) => ({
  id: Number(metric.id ?? 0),
  registeredAt: metric.registrada_en ?? metric.registeredAt ?? metric.created_at ?? '',
  boxId: metric.id_caja ?? metric.boxId ?? metric.caja ?? null,
  waitSeconds: Number(
    metric.tiempo_medio_espera_segundos ??
      metric.waitSeconds ??
      metric.tiempo_espera ??
      metric.value ??
      0,
  ),
  source: metric.fuente ?? metric.source ?? 'desconocida',
})

const unpackMetrics = (data) => {
  const list = data?.metricas ?? data?.metrics ?? data?.data ?? data ?? []
  return Array.isArray(list) ? list : []
}

const loadMetrics = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    let lastError = null

    for (const endpoint of endpointCandidates) {
      try {
        const data = await requestJson(`${endpoint}?limite=${selectedLimit.value}`)
        metrics.value = unpackMetrics(data)
          .map(normalizeMetric)
          .filter((metric) => metric.waitSeconds >= 0)
          .sort((a, b) => new Date(a.registeredAt) - new Date(b.registeredAt))
        return
      } catch (error) {
        lastError = error
      }
    }

    throw lastError
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? `${error.message}. Revisa que el backend exponga GET /api/v1/metricas.`
        : 'No se han podido cargar las metricas.'
  } finally {
    loading.value = false
  }
}

const boxOptions = computed(() => {
  const boxes = new Set(metrics.value.map((metric) => metric.boxId || 'global'))
  return ['todas', ...Array.from(boxes).sort()]
})

const filteredMetrics = computed(() => {
  if (selectedBox.value === 'todas') return metrics.value
  if (selectedBox.value === 'global') return metrics.value.filter((metric) => !metric.boxId)
  return metrics.value.filter((metric) => metric.boxId === selectedBox.value)
})

const latestMetric = computed(() => filteredMetrics.value.at(-1) ?? null)

const averageWait = computed(() => {
  if (!filteredMetrics.value.length) return 0
  const total = filteredMetrics.value.reduce((sum, metric) => sum + metric.waitSeconds, 0)
  return total / filteredMetrics.value.length
})

const maxWait = computed(() =>
  filteredMetrics.value.reduce((max, metric) => Math.max(max, metric.waitSeconds), 0),
)

const minWait = computed(() =>
  filteredMetrics.value.reduce(
    (min, metric) => Math.min(min, metric.waitSeconds),
    filteredMetrics.value[0]?.waitSeconds ?? 0,
  ),
)

const trend = computed(() => {
  const list = filteredMetrics.value
  if (list.length < 2) return 0

  const previous = list.at(-2).waitSeconds
  const latest = list.at(-1).waitSeconds
  return latest - previous
})

const groupedByBox = computed(() => {
  const groups = new Map()

  for (const metric of metrics.value) {
    const key = metric.boxId || 'global'
    const group = groups.get(key) ?? {
      id: key,
      label: key === 'global' ? 'Global' : key,
      count: 0,
      total: 0,
      latest: 0,
    }

    group.count += 1
    group.total += metric.waitSeconds
    group.latest = metric.waitSeconds
    groups.set(key, group)
  }

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      average: group.count ? group.total / group.count : 0,
    }))
    .sort((a, b) => b.average - a.average)
})

const chartPoints = computed(() => {
  const list = filteredMetrics.value
  if (!list.length) return ''

  const width = 760
  const height = 250
  const padding = 18
  const max = Math.max(...list.map((metric) => metric.waitSeconds), 1)
  const min = Math.min(...list.map((metric) => metric.waitSeconds), 0)
  const range = Math.max(max - min, 1)

  return list
    .map((metric, index) => {
      const x =
        list.length === 1
          ? width / 2
          : padding + (index / (list.length - 1)) * (width - padding * 2)
      const y = height - padding - ((metric.waitSeconds - min) / range) * (height - padding * 2)
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
})

const chartArea = computed(() => (chartPoints.value ? `${chartPoints.value} 742,250 18,250` : ''))

const recentMetrics = computed(() => filteredMetrics.value.slice(-8).reverse())

const formatSeconds = (seconds) => {
  if (!Number.isFinite(seconds)) return '0 s'
  if (seconds < 60) return `${seconds.toFixed(1)} s`
  return `${(seconds / 60).toFixed(1)} min`
}

const formatDate = (value) => {
  if (!value) return 'Sin fecha'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const barWidth = (value) => {
  const max = Math.max(...groupedByBox.value.map((group) => group.average), 1)
  return `${Math.max((value / max) * 100, 4)}%`
}

onMounted(loadMetrics)
</script>

<template>
  <main class="graphics-page">
    <section class="page-shell">
      <header class="hero">
        <RouterLink class="back-link" :to="{ name: 'menu' }">
          <span class="back-arrow">←</span> Volver al menú
        </RouterLink>
        <span class="kicker">SmartQ</span>

        <div class="hero-content">
          <div>
            <h1>Gráficas y estadísticas</h1>
            <p>
              Consulta la evolución del tiempo medio de espera registrado en la tabla de métricas.
            </p>
          </div>

          <div class="summary">
            <strong>{{ metrics.length }}</strong>
            <span>registros</span>
            <strong>{{ groupedByBox.length }}</strong>
            <span>segmentos</span>
          </div>
        </div>

        <div class="toolbar">
          <label>
            Segmento
            <select v-model="selectedBox" :disabled="loading">
              <option v-for="box in boxOptions" :key="box" :value="box">
                {{ box === 'todas' ? 'Todas las cajas' : box === 'global' ? 'Global' : box }}
              </option>
            </select>
          </label>

          <label>
            Límite
            <select v-model.number="selectedLimit" :disabled="loading" @change="loadMetrics">
              <option :value="50">50 registros</option>
              <option :value="100">100 registros</option>
              <option :value="250">250 registros</option>
              <option :value="500">500 registros</option>
            </select>
          </label>

          <button type="button" :disabled="loading" @click="loadMetrics">
            {{ loading ? 'Cargando...' : 'Recargar datos' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="status-message error" role="alert">{{ errorMessage }}</p>
      <p v-else-if="loading" class="status-message">Cargando métricas...</p>

      <section class="stats-grid" aria-label="Resumen de metricas">
        <article class="stat-card">
          <span>Espera actual</span>
          <strong>{{ formatSeconds(latestMetric?.waitSeconds ?? 0) }}</strong>
          <small>{{ latestMetric ? formatDate(latestMetric.registeredAt) : 'Sin datos' }}</small>
        </article>

        <article class="stat-card">
          <span>Media</span>
          <strong>{{ formatSeconds(averageWait) }}</strong>
          <small>{{ filteredMetrics.length }} muestras visibles</small>
        </article>

        <article class="stat-card">
          <span>Máximo</span>
          <strong>{{ formatSeconds(maxWait) }}</strong>
          <small>Mínimo {{ formatSeconds(minWait) }}</small>
        </article>

        <article class="stat-card">
          <span>Tendencia</span>
          <strong :class="{ positive: trend > 0, negative: trend < 0 }">
            {{ trend > 0 ? '+' : '' }}{{ formatSeconds(trend) }}
          </strong>
          <small>Respecto a la muestra anterior</small>
        </article>
      </section>

      <section class="content-grid">
        <article class="chart-card">
          <div class="section-heading">
            <div>
              <h2>Evolución temporal</h2>
              <p>Tiempo medio de espera por muestra registrada.</p>
            </div>
            <span>{{ filteredMetrics.length }} puntos</span>
          </div>

          <div v-if="filteredMetrics.length" class="line-chart" role="img" aria-label="Grafica de evolucion temporal">
            <svg viewBox="0 0 760 250" preserveAspectRatio="none">
              <line x1="18" y1="232" x2="742" y2="232" />
              <line x1="18" y1="18" x2="18" y2="232" />
              <polygon :points="chartArea" />
              <polyline :points="chartPoints" />
            </svg>
            <div class="chart-scale">
              <span>{{ formatSeconds(maxWait) }}</span>
              <span>{{ formatSeconds(minWait) }}</span>
            </div>
          </div>

          <div v-else class="empty-state">
            No hay métricas para este filtro.
          </div>
        </article>

        <aside class="side-panel">
          <article class="panel-block">
            <div class="section-heading compact">
              <h2>Por caja</h2>
              <span>{{ groupedByBox.length }}</span>
            </div>

            <div v-if="groupedByBox.length" class="bar-list">
              <div v-for="group in groupedByBox" :key="group.id" class="bar-row">
                <div class="bar-label">
                  <strong>{{ group.label }}</strong>
                  <span>{{ formatSeconds(group.average) }}</span>
                </div>
                <div class="bar-track">
                  <span :style="{ width: barWidth(group.average) }"></span>
                </div>
              </div>
            </div>

            <div v-else class="empty-state compact">Sin datos por caja.</div>
          </article>

          <article class="panel-block">
            <div class="section-heading compact">
              <h2>Últimas métricas</h2>
              <span>{{ recentMetrics.length }}</span>
            </div>

            <ol v-if="recentMetrics.length" class="recent-list">
              <li v-for="metric in recentMetrics" :key="metric.id || `${metric.registeredAt}-${metric.boxId}`">
                <span>
                  <strong>{{ metric.boxId || 'Global' }}</strong>
                  <small>{{ formatDate(metric.registeredAt) }}</small>
                </span>
                <b>{{ formatSeconds(metric.waitSeconds) }}</b>
              </li>
            </ol>

            <div v-else class="empty-state compact">Sin registros recientes.</div>
          </article>
        </aside>
      </section>
    </section>
  </main>
</template>

<style scoped>
.graphics-page {
  min-height: 100vh;
  padding: 32px;
  background:
    radial-gradient(circle at top left, rgba(0, 132, 61, 0.16), transparent 28%),
    linear-gradient(135deg, #f5f8f3 0%, #e9f1ea 48%, #f8faf8 100%);
  color: #173326;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.page-shell {
  width: min(1180px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 24px;
}

.hero {
  display: grid;
  gap: 16px;
}

.back-link {
  width: fit-content;
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

.kicker {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(0, 132, 61, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #007d3a;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
}

h1 {
  margin: 0 0 10px;
  font-size: clamp(2.4rem, 6vw, 4.5rem);
  line-height: 1;
}

p {
  max-width: 720px;
  margin: 0;
  color: #506459;
  font-size: 1.08rem;
  line-height: 1.6;
}

.summary {
  min-width: 168px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  padding: 18px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 16px 38px rgba(23, 51, 38, 0.1);
}

.summary strong {
  color: #00843d;
  font-size: 1.55rem;
  line-height: 1;
}

.summary span {
  align-self: center;
  color: #627267;
  font-size: 0.92rem;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: end;
  padding: 20px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 18px 44px rgba(23, 51, 38, 0.1);
}

label {
  min-width: 170px;
  display: grid;
  gap: 8px;
  color: #506459;
  font-size: 0.9rem;
  font-weight: 800;
}

select {
  width: 100%;
  min-height: 46px;
  box-sizing: border-box;
  border: 1px solid rgba(23, 51, 38, 0.18);
  border-radius: 8px;
  padding: 0 14px;
  background: #ffffff;
  color: #173326;
  font: inherit;
}

select:focus {
  border-color: #00843d;
  outline: 3px solid rgba(0, 132, 61, 0.18);
}

button {
  min-height: 46px;
  padding: 0 18px;
  border: 0;
  border-radius: 8px;
  background: #00843d;
  color: #ffffff;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.status-message {
  margin: 0;
  padding: 14px 16px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.84);
  color: #506459;
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.45;
}

.status-message.error {
  border-color: rgba(215, 25, 32, 0.22);
  background: rgba(215, 25, 32, 0.08);
  color: #9f151a;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card,
.chart-card,
.panel-block {
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 42px rgba(23, 51, 38, 0.1);
}

.stat-card {
  display: grid;
  gap: 8px;
  padding: 18px;
}

.stat-card span,
.stat-card small,
.section-heading span,
.recent-list small,
.bar-label span {
  color: #627267;
  font-size: 0.84rem;
  font-weight: 800;
}

.stat-card strong {
  overflow-wrap: anywhere;
  color: #00843d;
  font-size: clamp(1.5rem, 3vw, 2.15rem);
  line-height: 1;
}

.stat-card strong.positive {
  color: #d71920;
}

.stat-card strong.negative {
  color: #00843d;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(300px, 0.85fr);
  gap: 16px;
  align-items: start;
}

.chart-card,
.panel-block {
  display: grid;
  gap: 18px;
  padding: 20px;
}

.side-panel {
  display: grid;
  gap: 16px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: start;
}

.section-heading.compact {
  align-items: center;
}

h2 {
  margin: 0;
  font-size: 1.35rem;
}

.section-heading p {
  margin-top: 6px;
  font-size: 0.95rem;
}

.line-chart {
  position: relative;
  min-height: 300px;
  border: 1px solid rgba(23, 51, 38, 0.1);
  border-radius: 8px;
  background:
    linear-gradient(rgba(23, 51, 38, 0.06) 1px, transparent 1px),
    #ffffff;
  background-size: 100% 58px;
  overflow: hidden;
}

.line-chart svg {
  width: 100%;
  height: 300px;
  display: block;
}

.line-chart line {
  stroke: rgba(23, 51, 38, 0.16);
  stroke-width: 2;
}

.line-chart polygon {
  fill: rgba(0, 132, 61, 0.1);
}

.line-chart polyline {
  fill: none;
  stroke: #00843d;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 4;
}

.chart-scale {
  position: absolute;
  inset: 14px auto 14px 14px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: #627267;
  font-size: 0.78rem;
  font-weight: 800;
  pointer-events: none;
}

.bar-list,
.recent-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.bar-row {
  display: grid;
  gap: 8px;
}

.bar-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.bar-label strong,
.recent-list strong {
  font-size: 0.95rem;
}

.bar-track {
  height: 12px;
  border-radius: 999px;
  background: #eef4ed;
  overflow: hidden;
}

.bar-track span {
  height: 100%;
  display: block;
  border-radius: inherit;
  background: linear-gradient(90deg, #00843d, #d71920);
}

.recent-list li {
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(23, 51, 38, 0.1);
}

.recent-list li:last-child {
  border-bottom: 0;
}

.recent-list span {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.recent-list b {
  color: #00843d;
  white-space: nowrap;
}

.empty-state {
  min-height: 180px;
  display: grid;
  place-items: center;
  border: 1px dashed rgba(23, 51, 38, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.58);
  color: #627267;
  font-weight: 800;
  text-align: center;
}

.empty-state.compact {
  min-height: 96px;
}

@media (max-width: 980px) {
  .hero-content,
  .content-grid,
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .summary {
    width: fit-content;
  }
}

@media (max-width: 680px) {
  .graphics-page {
    padding: 24px 18px;
  }

  .toolbar,
  .section-heading {
    display: grid;
  }

  label {
    min-width: 0;
  }
}
</style>
