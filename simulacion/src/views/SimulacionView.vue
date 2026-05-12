<template>
  <RenderCajas :simulacion="simulacion" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Simulacion from '../models/Simulacion.js'
import RenderCajas from '../components/RenderCajas.vue'

const simulacion = ref(null)
simulacion.value = new Simulacion(6)
onMounted(() => {
  console.log(simulacion.value)
})
</script>

<style></style>
