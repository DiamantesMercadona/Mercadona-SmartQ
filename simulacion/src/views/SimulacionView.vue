<template>
  <div class="simulacion-view">
    <RenderCajas :simulacion="simulacion" />

    <div class="backend-status">
      <span class="status-dot" :class="backendStatus"></span>
      <span class="status-label">{{ statusLabel }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import Simulacion from '../models/Simulacion.js'
import RenderCajas from '../components/RenderCajas.vue'

const POLLING_INTERVAL_MS = 5000

const simulacion = ref(null)
const backendStatus = ref('disconnected')

const statusLabel = computed(() => {
  if (backendStatus.value === 'connected') return 'Backend'
  if (backendStatus.value === 'error') return 'Sin backend'
  return 'Conectando...'
})

async function pingBackend() {
  try {
    await simulacion.value?.refrescarEstadoCajas()
    backendStatus.value = 'connected'
  } catch {
    backendStatus.value = 'error'
  }
}

let pollingInterval = null

onMounted(async () => {
  simulacion.value = new Simulacion()
  await simulacion.value.inicializar()

  await pingBackend()
  pollingInterval = setInterval(pingBackend, POLLING_INTERVAL_MS)
})

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
})
</script>

<style scoped>
.simulacion-view {
  position: relative;
}

.backend-status {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  border-radius: 8px;
  background: rgba(17, 24, 39, 0.85);
  backdrop-filter: blur(6px);
  box-shadow: 0 4px 16px rgba(2, 6, 23, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.12);
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
</style>
