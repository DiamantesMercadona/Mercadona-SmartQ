<template>
  <div ref="container" class="scene"></div>

  <!-- Controls panel -->
  <div class="controls-panel">
    <label>
      Velocidad: <strong>{{ simulationSpeed.toFixed(2) }}x</strong>
      <input type="range" v-model.number="simulationSpeed" min="0.25" max="5" step="0.25" />
    </label>
    <label>
      Cámara:
      <select v-model="cameraMode">
        <option value="libre">Libre</option>
        <option value="frontal">Frontal</option>
        <option value="cenital">Cenital</option>
      </select>
    </label>
    <label class="toggle">
      <input type="checkbox" v-model="mostrarReferenciasEspaciales" /> Referencias espaciales
    </label>
    <label class="toggle"> <input type="checkbox" v-model="mostrarLabels" /> Etiquetas </label>
    <label class="toggle">
      <input type="checkbox" v-model="saveFrames" /> Enviar frames al servidor
    </label>
    <button
      type="button"
      class="btn-download"
      :class="{ 'is-recording': isRecordingVideo }"
      @click="toggleVideoRecording"
    >
      {{ isRecordingVideo ? 'Detener grabación' : 'Grabar video' }}
    </button>
    <span v-if="isRecordingVideo" class="recording-time">{{ recordingElapsedLabel }}</span>
    <button @click="downloadFrame" class="btn-download">Descargar frame</button>
  </div>

  <!-- Tooltips for cajas -->
  <div v-for="c in cajas" :key="c.id" class="tooltip" :style="tooltips.getStyle(c.id)">
    <div class="tooltip-card" v-if="mostrarLabels">
      <div class="tooltip-header">
        <strong>Caja {{ c.id }}</strong>
        <div :class="['status-badge', c.abierta ? 'open' : 'closed']">
          {{ c.abierta ? 'Abierta' : 'Cerrada' }}
        </div>
      </div>
      <div class="tooltip-content">👥 {{ c.cola.length }} en cola</div>
    </div>
  </div>

  <!-- Free camera position panel -->
  <div v-if="mostrarReferenciasEspaciales && cameraMode === 'libre'" class="camera-pos-panel">
    <code class="camera-pos-coords"
      >new THREE.Vector3({{ camera.position.x.toFixed(2) }}, {{ camera.position.y.toFixed(2) }},
      {{ camera.position.z.toFixed(2) }})</code
    >
    <button
      class="btn-copy-coords"
      :class="{ copied: posicionCopiada }"
      @click="copiarPosicionCamara"
    >
      {{ posicionCopiada ? '✓' : 'Copiar' }}
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import './RenderCajas.css'
import * as THREE from 'three'
import FrameStreamer from '@/utils/frameStreamer.js'
import { createVideoRecorder } from '@/utils/videoRecorder.js'

import { crearFondoEscena, crearSuelo, crearLuces } from '@/composables/useSceneSetup.js'
import { crearParedes } from '@/composables/useWalls.js'
import { useTooltips } from '@/composables/useTooltips.js'
import {
  cargarModeloCaja,
  renderizarCajas,
  syncScene,
  tickAnimations,
  simulationSpeed,
} from '@/composables/useCajasScene.js'
import { initCameraControls, POSICIONES_CAMARA } from '@/composables/useCameraControls.js'
import { useReferenciasEspaciales } from '@/composables/useReferenciasEspaciales.js'

const SUELO_LARGO = 40
const SUELO_ANCHO = 32

const props = defineProps({
  simulacion: { type: Object, default: null },
})

const container = ref(null)
const cajas = computed(() => props.simulacion?.cajas ?? [])

const saveFrames = ref(false)
const isRecordingVideo = ref(false)
const recordingElapsedSeconds = ref(0)
const cameraMode = ref('libre')
const mostrarReferenciasEspaciales = ref(false)
const mostrarLabels = ref(false)
const posicionCopiada = ref(false)

const tooltips = useTooltips()
const refEspaciales = useReferenciasEspaciales(SUELO_LARGO, SUELO_ANCHO)

let scene, camera, renderer, animationId, cajaModelo, camControls, videoRecorder
const cajasMesh = []
const frameStreamer = new FrameStreamer()

const recordingElapsedLabel = computed(() => {
  const m = Math.floor(recordingElapsedSeconds.value / 60)
  const s = recordingElapsedSeconds.value % 60
  return `Grabando ${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

async function init() {
  scene = new THREE.Scene()
  scene.background = crearFondoEscena()

  camera = new THREE.PerspectiveCamera(
    55,
    container.value.clientWidth / container.value.clientHeight,
    0.1,
    100,
  )
  camera.position.copy(POSICIONES_CAMARA[cameraMode.value])

  renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  renderer.shadowMap.enabled = true
  container.value.appendChild(renderer.domElement)

  camControls = initCameraControls(camera, renderer, cameraMode.value)
  window.addEventListener('keydown', camControls.onKeyDown)
  window.addEventListener('keyup', camControls.onKeyUp)

  crearLuces(scene, SUELO_LARGO)

  const suelo = crearSuelo(SUELO_LARGO, SUELO_ANCHO)
  suelo.rotation.x = -Math.PI / 2
  suelo.receiveShadow = true
  scene.add(suelo)

  await crearParedes(scene, SUELO_LARGO, SUELO_ANCHO)

  if (mostrarReferenciasEspaciales.value) refEspaciales.crear(scene)

  cargarModeloCaja().then((modelo) => {
    cajaModelo = modelo
    renderizarCajas(scene, cajas.value, cajaModelo, cajasMesh, tooltips.initForCaja)
  })

  animate()

  if (saveFrames.value) {
    frameStreamer
      .startStreaming(renderer, 10)
      .catch((e) => console.error('FrameStreamer error:', e))
  }
  window.addEventListener('resize', onResize)
}

function animate() {
  animationId = requestAnimationFrame(animate)
  camControls.controls.update()
  camControls.updateWASD()
  tickAnimations()

  cajasMesh.forEach((mesh) => {
    const id = mesh.userData?.caja?.id
    if (id != null) tooltips.updatePosition(mesh, id, camera, renderer)
  })

  renderer.render(scene, camera)
}

function onResize() {
  if (!container.value) return
  camera.aspect = container.value.clientWidth / container.value.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
}

function copiarPosicionCamara() {
  const { x, y, z } = camera.position
  navigator.clipboard.writeText(
    `new THREE.Vector3(${x.toFixed(2)}, ${y.toFixed(2)}, ${z.toFixed(2)})`,
  )
  posicionCopiada.value = true
  setTimeout(() => (posicionCopiada.value = false), 1500)
}

function downloadFrame() {
  if (!renderer) return
  renderer.domElement.toBlob(
    (blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `frame-${Date.now()}.jpg`
      a.click()
      URL.revokeObjectURL(url)
    },
    'image/jpeg',
    0.95,
  )
}

function toggleVideoRecording() {
  if (!videoRecorder && renderer) {
    videoRecorder = createVideoRecorder(renderer, { fps: 30, filenamePrefix: 'render' })
  }
  if (isRecordingVideo.value) {
    videoRecorder?.stop()
    return
  }
  const started = videoRecorder?.start({
    onTick: (s) => {
      recordingElapsedSeconds.value = s
    },
    onStart: () => {
      isRecordingVideo.value = true
      recordingElapsedSeconds.value = 0
    },
    onStop: () => {
      isRecordingVideo.value = false
      recordingElapsedSeconds.value = 0
    },
  })
  if (!started) {
    isRecordingVideo.value = false
    recordingElapsedSeconds.value = 0
  }
}

watch(saveFrames, async (val) => {
  if (val) {
    if (!renderer) return
    try {
      await frameStreamer.startStreaming(renderer, 10)
    } catch (e) {
      console.error('No se pudo iniciar FrameStreamer:', e)
      saveFrames.value = false
    }
  } else {
    frameStreamer.stopStreaming()
    frameStreamer.disconnect()
  }
})

watch(mostrarReferenciasEspaciales, (val) => {
  if (!scene) return
  if (val) refEspaciales.crear(scene)
  else refEspaciales.limpiar(scene)
})

watch(cameraMode, (mode) => {
  if (camControls) camControls.setMode(mode)
})

// Rebuild cajas only when their count changes (e.g. a new caja is added/removed).
watch(
  () => props.simulacion?.cajas?.length,
  () => {
    if (scene && cajaModelo)
      renderizarCajas(scene, cajas.value, cajaModelo, cajasMesh, tooltips.initForCaja)
  },
)

// Animate queue / state changes (client joins or leaves).
watch(
  () => props.simulacion,
  () => syncScene(cajas.value, cajasMesh),
  { deep: true, immediate: true },
)

onMounted(init)

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', camControls?.onKeyDown)
  window.removeEventListener('keyup', camControls?.onKeyUp)
  camControls?.controls?.dispose()
  refEspaciales.limpiar(scene)
  videoRecorder?.dispose()
  renderer?.dispose()
  frameStreamer.stopStreaming()
  frameStreamer.disconnect()
})
</script>
