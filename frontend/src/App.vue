<!-- <script setup>
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style scoped></style> -->

<template>
  <div id="app">
    <TestThreejs />
  </div>
</template>

<script>
import TestThreejs from './TestThreejs.vue'
export default {
  name: 'App',
  components: {
    TestThreejs,
  },
}
</script>

<style></style>
