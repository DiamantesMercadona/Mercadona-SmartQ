<template>
  <RenderCajas :simulacion="simulacion" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Simulacion from '../models/Simulacion.js'
import Cliente from '@/models/Cliente.js'
import RenderCajas from '../components/RenderCajas.vue'

const simulacion = ref(null)
const tiempoUpdateTestSec = 2
simulacion.value = new Simulacion(6)

function updateSimulacion() {
  simulacion.value.cajas.forEach((caja) => {
    const agregarCliente = Math.random() < 0.5
    if (agregarCliente) {
      caja.cola.push(new Cliente())
    } else {
      if (caja.cola.length > 0) {
        caja.cola.shift()
      }
    }
    caja.abierta = caja.cola.length > 0
  })
}

onMounted(() => {
  setInterval(() => {
    updateSimulacion()
    console.log(simulacion.value)
  }, tiempoUpdateTestSec * 1000)
})
</script>

<style></style>
