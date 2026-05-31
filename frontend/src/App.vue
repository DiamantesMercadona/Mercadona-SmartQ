<script setup>
import { ref } from 'vue'
import { useRouter, RouterView } from 'vue-router'

const router = useRouter()
const isRouteLoading = ref(false)

router.beforeEach((to, from, next) => {
  isRouteLoading.value = true
  setTimeout(() => {
    next()
  }, 350)
})

router.afterEach(() => {
  setTimeout(() => {
    isRouteLoading.value = false
  }, 150)
})
</script>

<template>
  <div class="app-root">
    <!-- Sleek route transition loader -->
    <Transition name="fade">
      <div v-if="isRouteLoading" class="global-route-loader">
        <div class="loader-content">
          <div class="spinner-ring">
            <div></div><div></div><div></div><div></div>
          </div>
          <span class="loader-brand">
            Mercadona <strong class="brand-highlight">SmartQ</strong>
          </span>
        </div>
      </div>
    </Transition>
    
    <RouterView />
  </div>
</template>

<style>
/* Global resets for scrollbars and layout */
html, body {
  margin: 0;
  padding: 0;
  background-color: #f5f8f3;
  overflow-x: hidden;
}

.app-root {
  min-height: 100vh;
  position: relative;
}

/* Glassmorphic route loader styling */
.global-route-loader {
  position: fixed;
  inset: 0;
  z-index: 99999;
  background: rgba(245, 248, 243, 0.88);
  backdrop-filter: blur(16px);
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.3s ease;
}

.loader-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.spinner-ring {
  display: inline-block;
  position: relative;
  width: 64px;
  height: 64px;
}
.spinner-ring div {
  box-sizing: border-box;
  display: block;
  position: absolute;
  width: 48px;
  height: 48px;
  margin: 8px;
  border: 4px solid #00843d;
  border-radius: 50%;
  animation: spinner-ring-animation 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
  border-color: #00843d transparent transparent transparent;
}
.spinner-ring div:nth-child(1) { animation-delay: -0.45s; }
.spinner-ring div:nth-child(2) { animation-delay: -0.3s; }
.spinner-ring div:nth-child(3) { animation-delay: -0.15s; }

@keyframes spinner-ring-animation {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loader-brand {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.15rem;
  color: #173326;
  font-weight: 500;
  letter-spacing: -0.01em;
}
.brand-highlight {
  color: #00843d;
  font-weight: 800;
}

/* Fade animation rules */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
