<template>
  <RenderCajas :cajas="cajas" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import RenderCajas from '../components/RenderCajas.vue'

const segundosRefresco = 5

const cajas = ref([
  { id: 1, abierta: true, cola: 2 },
  { id: 2, abierta: true, cola: 4 },
  { id: 3, abierta: false, cola: 0 },
  { id: 4, abierta: true, cola: 1 },
  { id: 5, abierta: false, cola: 0 },
  { id: 6, abierta: true, cola: 3 },
])


function actualizarCajas() {
  setInterval(() => {
    cajas.value = cajas.value.map(caja => {
      const nuevaCola = Math.max(0, caja.cola + (Math.random() > 0.5 ? 1 : -1))
      if (nuevaCola === 0) {
        return { ...caja, abierta: false, cola: 0 }
      } else {
        return { ...caja, abierta: true, cola: nuevaCola }
      }
    })
  }, segundosRefresco * 1000)
}

onMounted(() => {
  // actualizarCajas()
})

</script>

<style></style>
