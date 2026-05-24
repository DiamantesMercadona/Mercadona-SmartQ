<template>
  <div class="simulacion-view">
    <RenderCajas :simulacion="simulacion" />

    <div class="ui-controls" v-if="simulacion">
      <div class="ui-row backend-status">
        <span class="status-dot" :class="backendStatus"></span>
        <span class="status-label">{{ statusLabel }}</span>
      </div>
      <div class="ui-row">
        <select id="cajaSelect" v-model.number="selectedCajaId">
          <option v-for="caja in simulacion.cajas" :key="caja.id" :value="caja.id">
            Caja {{ caja.id }}
          </option>
        </select>
        <span
          class="estado-dot"
          :class="currentCaja?.abierta ? 'abierta' : 'cerrada'"
          :title="currentCaja?.abierta ? 'Abierta' : 'Cerrada'"
        ></span>
      </div>
      <div class="ui-row">
        <button type="button" @click="abrirCajaUI">Abrir</button>
        <button type="button" @click="cerrarCajaUI">Cerrar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import Simulacion from '../models/Simulacion.js'
import RenderCajas from '../components/RenderCajas.vue'
import { getQueues } from '../services/backendApi.js'

const simulacion = ref(null)
const selectedCajaId = ref(0)
const backendStatus = ref('disconnected')

simulacion.value = new Simulacion(6)

const currentCaja = computed(() => simulacion.value?.obtenerCaja(selectedCajaId.value) ?? null)

const statusLabel = computed(() => {
  if (backendStatus.value === 'connected') return 'Backend'
  if (backendStatus.value === 'error') return 'Sin backend'
  return 'Conectando...'
})

async function pingBackend() {
  try {
    await getQueues()
    backendStatus.value = 'connected'
  } catch {
    backendStatus.value = 'error'
  }
}

let pollingInterval = null

onMounted(async () => {
  await pingBackend()
  pollingInterval = setInterval(pingBackend, 5000)
})

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
})

function abrirCajaUI() {
  if (!simulacion.value) return
  simulacion.value.abrirCaja(selectedCajaId.value)
}

function cerrarCajaUI() {
  if (!simulacion.value) return
  simulacion.value.cerrarCaja(selectedCajaId.value)
}
</script>

<style scoped>
.simulacion-view {
  position: relative;
}

.ui-controls {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(17, 24, 39, 0.85);
  color: #e5e7eb;
  font-size: 11px;
  backdrop-filter: blur(6px);
  box-shadow: 0 4px 16px rgba(2, 6, 23, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.ui-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.backend-status {
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  margin-bottom: 2px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.connected {
  background: #10b981;
  box-shadow: 0 0 4px rgba(16, 185, 129, 0.7);
}

.status-dot.disconnected {
  background: #94a3b8;
}

.status-dot.error {
  background: #f59e0b;
  box-shadow: 0 0 4px rgba(245, 158, 11, 0.7);
}

.status-label {
  font-size: 9px;
  color: #94a3b8;
  letter-spacing: 0.03em;
}

.ui-controls select,
.ui-controls button {
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 6px;
  padding: 3px 8px;
  background: rgba(30, 41, 59, 0.9);
  color: #e5e7eb;
  font-size: 11px;
  font-weight: 600;
}

.ui-controls button {
  cursor: pointer;
  transition: background 0.1s ease;
}

.ui-controls button:hover {
  background: rgba(51, 65, 85, 0.95);
}

.ui-controls button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.estado-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.estado-dot.abierta {
  background: #10b981;
  box-shadow: 0 0 5px rgba(16, 185, 129, 0.7);
}

.estado-dot.cerrada {
  background: #ef4444;
  box-shadow: 0 0 5px rgba(239, 68, 68, 0.7);
}
</style>
