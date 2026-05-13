<template>
  <div class="simulacion-view">
    <RenderCajas :simulacion="simulacion" />

    <div class="ui-controls" v-if="simulacion">
      <label for="cajaSelect">Caja</label>
      <select id="cajaSelect" v-model.number="selectedCajaId">
        <option v-for="caja in simulacion.cajas" :key="caja.id" :value="caja.id">
          Caja {{ caja.id }}
        </option>
      </select>

      <span class="estado-caja" :class="currentCaja?.abierta ? 'abierta' : 'cerrada'">
        {{ currentCaja?.abierta ? 'Abierta' : 'Cerrada' }}
      </span>

      <button type="button" @click="abrirCajaUI">Abrir caja</button>
      <button type="button" @click="cerrarCajaUI">Cerrar caja</button>
      <button type="button" @click="agregarClienteUI" :disabled="!currentCaja?.abierta">
        Añadir cliente
      </button>
      <button type="button" @click="removerClienteUI">Eliminar cliente</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Simulacion from '../models/Simulacion.js'
import RenderCajas from '../components/RenderCajas.vue'

const simulacion = ref(null)
const selectedCajaId = ref(0)

simulacion.value = new Simulacion(6)

const currentCaja = computed(() => simulacion.value?.obtenerCaja(selectedCajaId.value) ?? null)

function abrirCajaUI() {
  if (!simulacion.value) return
  simulacion.value.abrirCaja(selectedCajaId.value)
}

function cerrarCajaUI() {
  if (!simulacion.value) return
  simulacion.value.cerrarCaja(selectedCajaId.value)
}

function agregarClienteUI() {
  if (!simulacion.value) return
  simulacion.value.agregarCliente(selectedCajaId.value)
}

function removerClienteUI() {
  if (!simulacion.value) return
  simulacion.value.removerCliente(selectedCajaId.value)
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
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(17, 24, 39, 0.85);
  color: #e5e7eb;
}

.ui-controls select,
.ui-controls button {
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 8px;
  padding: 6px 10px;
  background: #111827;
  color: #e5e7eb;
}

.ui-controls button {
  cursor: pointer;
}

.ui-controls button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.estado-caja {
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
}

.estado-caja.abierta {
  background: rgba(16, 185, 129, 0.2);
  color: #6ee7b7;
}

.estado-caja.cerrada {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}
</style>
