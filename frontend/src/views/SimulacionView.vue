<template>
  <RenderCajas :cajas="cajas" />
</template>

<script setup>
import { ref } from 'vue'
import RenderCajas from '../components/RenderCajas.vue'

const cajas = ref([
  { id: 1, abierta: true, cola: 2 },
  { id: 2, abierta: true, cola: 4 },
  { id: 3, abierta: false, cola: 0 },
  { id: 4, abierta: true, cola: 1 },
  { id: 5, abierta: false, cola: 0 },
  { id: 6, abierta: true, cola: 3 },
])
</script>

<style></style>
