<template>
  <div class="simulacion-view">
    <RenderCajas :simulacion="simulacion" />

    <!-- Panel derecho: cajas -->
    <div class="right-panel">
      <div class="cajas-panel" v-if="simulacion">
        <div class="cajas-panel-title">Cajas</div>
        <div v-for="caja in simulacion.cajas" :key="caja.id" class="caja-row">
          <span class="caja-dot" :class="caja.abierta ? 'open' : 'closed'"></span>
          <span class="caja-id">{{ caja.id }}</span>
          <span class="caja-cola">{{ caja.cola.length }} en cola</span>
          <button class="caja-btn" :disabled="caja.abierta" @click="simulacion.abrirCaja(caja.id)">
            Abrir
          </button>
          <button
            class="caja-btn"
            :disabled="!caja.abierta"
            @click="simulacion.cerrarCaja(caja.id)"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import Simulacion from '../models/Simulacion.js'
import RenderCajas from '../components/RenderCajas.vue'

const POLLING_INTERVAL_MS = 5000

const simulacion = ref(null)

async function pingBackend() {
  await simulacion.value?.refrescarEstadoCajas()
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

<style scoped src="./SimulacionView.css"></style>
