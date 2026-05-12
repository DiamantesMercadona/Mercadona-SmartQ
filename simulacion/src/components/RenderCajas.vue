<template>
  <div ref="container" class="scene"></div>

  <!-- Constroles camara y toggles -->
  <div class="controls-panel">
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
    <button @click="downloadFrame" class="btn-download">Descargar frame</button>
  </div>

  <!-- Tooltips cajas -->
  <div>
    <div v-for="c in cajas" :key="c.id" class="tooltip" :style="getTooltipStyle(c.id)">
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
  </div>

  <div>
    <!-- Mostrar cordenadas free cam -->
    <div v-if="mostrarReferenciasEspaciales && cameraMode === 'libre'" class="modal-top">
      <div class="modal">
        <div class="modal-header">
          <h2>Cámara Libre</h2>
        </div>
        <div style="padding: 18px 24px">
          <div class="info-row">
            <span class="info-label">Posición:</span>
            <span class="info-value">
              ({{ camera.position.x.toFixed(1) }}, {{ camera.position.y.toFixed(1) }},
              {{ camera.position.z.toFixed(1) }})
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, reactive, computed, watch, render } from 'vue'
import './RenderCajas.css'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { getRandomFace, getAlvaroFace, imagenCarrito } from '@/utils/imagesUtils'
import FrameStreamer from '@/utils/frameStreamer.js'

const gtlfCajaPath = '/assets/3dmodels/psx_cashier_stand/scene.gltf'

const props = defineProps({
  simulacion: {
    type: Object,
    default: null,
  },
})

const saveFrames = ref(false)

const cajas = computed(() => props.simulacion?.cajas ?? [])

const sizeCaja = 1.5
const separacionCajas = 2.2 + sizeCaja
const cajasPorGrupo = 3
const espacioGrupos = 2.5

const sueloLargo = 40
const sueloAncho = 20

const faceScale = 0.75
const carritoScale = 2.7

const mostrarReferenciasEspaciales = ref(false)
const mostrarLabels = ref(true)

const cameraMode = ref('frontal') // libre, frontal, cenital. El por defecto no puese ser libre da error

const posicionesCamara = {
  frontal: new THREE.Vector3(-0.2, 9.2, 9.2),
  cenital: new THREE.Vector3(0, 20, 0.01),
}

const container = ref(null)
let scene, camera, renderer, animationId, gltfLoader, cajaModelo, controls, canvas
let referenciasEspaciales = []
const frameStreamer = new FrameStreamer()

// WASD camera movement
const keysPressed = { w: false, a: false, s: false, d: false }
const cameraWASDSpeed = 0.12

function onKeyDown(e) {
  const k = (e.key || '').toLowerCase()
  if (k in keysPressed) keysPressed[k] = true
}

function onKeyUp(e) {
  const k = (e.key || '').toLowerCase()
  if (k in keysPressed) keysPressed[k] = false
}

const cajasMesh = []

// posiciones de tooltip por caja id
const tooltipPositions = reactive({})

function initTooltipForCaja(id) {
  tooltipPositions[id] = { x: 0, y: 0, visible: false }
}

function getTooltipStyle(id) {
  const p = tooltipPositions[id]
  if (!p || !p.visible) return { display: 'none' }
  return {
    position: 'fixed',
    left: p.x + 'px',
    top: p.y + 'px',
    transform: 'translate(-50%, -160%)',
    pointerEvents: 'none',
    zIndex: 40,
  }
}

function updateTooltipPositionForId(mesh, id) {
  if (!mesh || !camera || !renderer || !container.value) return
  const worldPos = new THREE.Vector3()
  mesh.getWorldPosition(worldPos)

  const projected = worldPos.clone().project(camera)
  const rect = renderer.domElement.getBoundingClientRect()

  const x = ((projected.x + 1) / 2) * rect.width + rect.left
  const y = ((-projected.y + 1) / 2) * rect.height + rect.top

  tooltipPositions[id].x = Math.round(x)
  tooltipPositions[id].y = Math.round(y) - 48 // ajustar altura del tooltip
  tooltipPositions[id].visible = true
}

function cargarModeloCaja() {
  return new Promise((resolve) => {
    gltfLoader.load(gtlfCajaPath, (gltf) => {
      cajaModelo = gltf.scene
      cajaModelo.scale.set(sizeCaja, sizeCaja, sizeCaja)
      resolve(cajaModelo)
    })
  })
}

function limpiarCajasEscena() {
  cajasMesh.forEach((mesh) => {
    if (scene) scene.remove(mesh)
  })
  cajasMesh.length = 0
}

function limpiarReferenciasEspaciales() {
  referenciasEspaciales.forEach((objeto) => {
    if (scene) scene.remove(objeto)
  })
  referenciasEspaciales = []
}

function crearEtiquetaEje(texto, color) {
  canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 128
  const ctx = canvas.getContext('2d')

  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.font = 'bold 64px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#111827'
  ctx.strokeStyle = '#ffffff'
  ctx.lineWidth = 10
  ctx.strokeText(texto, canvas.width / 2, canvas.height / 2)
  ctx.fillStyle = color
  ctx.fillText(texto, canvas.width / 2, canvas.height / 2)

  const texture = new THREE.CanvasTexture(canvas)
  texture.needsUpdate = true

  const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
  const sprite = new THREE.Sprite(material)
  sprite.scale.set(0.9, 0.45, 1)
  return sprite
}

function crearReferenciasEspaciales() {
  if (!scene || !mostrarReferenciasEspaciales.value) return

  limpiarReferenciasEspaciales()

  const margen = 1.25
  const esquina = new THREE.Vector3(-sueloLargo / 2 + margen, 0.05, -sueloAncho / 2 + margen)

  const ejes = new THREE.AxesHelper(2)
  ejes.position.copy(esquina)
  scene.add(ejes)
  referenciasEspaciales.push(ejes)

  const etiquetaX = crearEtiquetaEje('X', '#ef4444')
  etiquetaX.position.set(esquina.x + 2.25, esquina.y + 0.12, esquina.z)
  scene.add(etiquetaX)
  referenciasEspaciales.push(etiquetaX)

  const etiquetaY = crearEtiquetaEje('Y', '#22c55e')
  etiquetaY.position.set(esquina.x, esquina.y + 2.15, esquina.z)
  scene.add(etiquetaY)
  referenciasEspaciales.push(etiquetaY)

  const etiquetaZ = crearEtiquetaEje('Z', '#3b82f6')
  etiquetaZ.position.set(esquina.x, esquina.y + 0.12, esquina.z + 2.25)
  scene.add(etiquetaZ)
  referenciasEspaciales.push(etiquetaZ)

  const centro = new THREE.Mesh(
    new THREE.SphereGeometry(0.12, 16, 16),
    new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.7 }),
  )
  centro.position.set(0, 0.12, 0)
  scene.add(centro)
  referenciasEspaciales.push(centro)

  const grid = new THREE.GridHelper(sueloLargo, sueloLargo, 0x9ca3af, 0x4b5563)
  grid.position.y = 0.01
  scene.add(grid)
  referenciasEspaciales.push(grid)
}

function renderizarCajas() {
  if (!scene || !cajaModelo) return

  limpiarCajasEscena()

  cajas.value.forEach((caja, i) => {
    const grupoIndex = Math.floor(i / cajasPorGrupo)
    const x =
      (i - (cajas.value.length - 1) / 2) * (separacionCajas + 0.5) + grupoIndex * espacioGrupos
    const modelo = crearCaja(caja, x)
    cajasMesh.push(modelo)
    scene.add(modelo)
    initTooltipForCaja(caja.id)
  })
}

function crearCaja(caja, x) {
  const grupo = new THREE.Group()
  grupo.position.x = x
  grupo.position.z = -7
  grupo.userData.caja = caja

  const modeloClone = cajaModelo.clone()
  grupo.add(modeloClone)

  const dependienteData = { color: 0x3b82f6, imagen: getAlvaroFace() }
  const dependiente = crearCliente(dependienteData)
  dependiente.position.set(1, 0, 0)
  grupo.add(dependiente)
  if (!caja.abierta) dependiente.visible = false

  grupo.userData.dependiente = dependiente
  grupo.userData.clientes = []
  actualizarCola(grupo, caja.cola)
  return grupo
}

function crearCarrito() {
  const g = new THREE.Group()

  const textureLoader = new THREE.TextureLoader()
  const carritoTexture = textureLoader.load(imagenCarrito)

  const carrito = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: carritoTexture, transparent: true }),
  )
  // usar la escala global para que el carrito sea del tamaño de la persona
  carrito.scale.set(carritoScale, carritoScale, 1)
  g.add(carrito)

  return g
}

function crearCliente(clienteData) {
  const g = new THREE.Group()

  const cuerpo = new THREE.Mesh(
    new THREE.CylinderGeometry(0.28, 0.32, 1.0, 20),
    new THREE.MeshStandardMaterial({ color: clienteData.color }),
  )
  cuerpo.position.y = 0.5
  g.add(cuerpo)

  // Cabeza como imagen sprite
  const textureLoader = new THREE.TextureLoader()
  const faceTexture = textureLoader.load(clienteData.imagen)
  const faceMaterial = new THREE.SpriteMaterial({ map: faceTexture, transparent: true })
  const cabeza = new THREE.Sprite(faceMaterial)
  cabeza.scale.set(faceScale, faceScale, 1)
  cabeza.position.y = 1.25
  g.add(cabeza)

  const brazoIzq = new THREE.Mesh(
    new THREE.BoxGeometry(0.12, 0.55, 0.12),
    new THREE.MeshStandardMaterial({ color: 0xf1c27d }),
  )
  brazoIzq.position.set(-0.35, 0.7, 0)
  g.add(brazoIzq)

  const brazoDer = brazoIzq.clone()
  brazoDer.position.x = 0.35
  g.add(brazoDer)

  // Añadir carrito solo si el cliente lo utiliza
  if (clienteData.usaCarrito) {
    const carrito = crearCarrito()
    // posicionar a la altura aproximada de la persona
    carrito.position.set(0.5, 1, 0.15)
    g.add(carrito)
  }

  return g
}

function actualizarCola(grupo, cola) {
  grupo.userData.clientes.forEach((c) => grupo.remove(c))
  grupo.userData.clientes = []
  if (!cola || cola.length < 1) return
    for (let i = 0; i < cola.length; i++) {
    const cliente = crearCliente(cola[i])
    const offsetX = Math.random() * 0.8 - 0.2
    cliente.position.set(1 + offsetX, 0, 2.5 + i * 1.25)
    // cliente.position.set(1, 0, 2.5 + i * 1.25)
    grupo.add(cliente)
    grupo.userData.clientes.push(cliente)
  }
}

function syncScene() {
  cajas.value.forEach((caja, i) => {
    if (!cajasMesh[i]) return
    actualizarCola(cajasMesh[i], caja.cola)
    cajasMesh[i].userData.dependiente.visible = caja.abierta
  })
}

function init() {
  scene = new THREE.Scene()

  // fondo
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 512
  const ctx = canvas.getContext('2d')

  // gradiente
  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height)
  gradient.addColorStop(0, '#1a1a2e')
  gradient.addColorStop(0.5, '#16213e')
  gradient.addColorStop(1, '#0f3460')

  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  const backgroundTexture = new THREE.CanvasTexture(canvas)
  scene.background = backgroundTexture

  // camara
  camera = new THREE.PerspectiveCamera(
    55,
    container.value.clientWidth / container.value.clientHeight,
    0.1,
    100,
  )
  camera.position.copy(posicionesCamara[cameraMode.value])

  // render
  // habilitar preserveDrawingBuffer para poder capturar el canvas luego
  renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  container.value.appendChild(renderer.domElement)

  //controles free cam
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.enabled = cameraMode.value === 'libre'
  // permitir zoom con la rueda y panning; ajustar distancias para permitir alejarse
  controls.enablePan = true
  controls.minDistance = 1
  controls.maxDistance = 80
  controls.update()

  // key listeners para movimiento WASD
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)

  // luces
  const ambient = new THREE.AmbientLight(0xffffff, 1.3)
  scene.add(ambient)

  const dir = new THREE.DirectionalLight(0xffffff, 1.2)
  dir.position.set(8, 12, 8)
  scene.add(dir)

  // suelo
  const tileCanvas = document.createElement('canvas')
  tileCanvas.width = 512
  tileCanvas.height = 512
  const tileCtx = tileCanvas.getContext('2d')

  tileCtx.fillStyle = '#4a5568'
  tileCtx.fillRect(0, 0, tileCanvas.width, tileCanvas.height)

  // azulejos
  tileCtx.strokeStyle = '#2d3748'
  tileCtx.lineWidth = 4
  const tileSize = 64
  for (let x = 0; x < tileCanvas.width; x += tileSize) {
    tileCtx.beginPath()
    tileCtx.moveTo(x, 0)
    tileCtx.lineTo(x, tileCanvas.height)
    tileCtx.stroke()
  }
  for (let y = 0; y < tileCanvas.height; y += tileSize) {
    tileCtx.beginPath()
    tileCtx.moveTo(0, y)
    tileCtx.lineTo(tileCanvas.width, y)
    tileCtx.stroke()
  }

  // efecto de brillo
  tileCtx.fillStyle = 'rgba(255, 255, 255, 0.1)'
  for (let x = 0; x < tileCanvas.width; x += tileSize) {
    for (let y = 0; y < tileCanvas.height; y += tileSize) {
      tileCtx.fillRect(x + 8, y + 8, tileSize - 16, tileSize - 16)
    }
  }

  const tileTexture = new THREE.CanvasTexture(tileCanvas)
  tileTexture.wrapS = THREE.RepeatWrapping
  tileTexture.wrapT = THREE.RepeatWrapping
  tileTexture.repeat.set(4, 4)

  // suelo con textura
  const suelo = new THREE.Mesh(
    new THREE.PlaneGeometry(sueloLargo, sueloAncho),
    new THREE.MeshStandardMaterial({
      color: 0x4a5568,
      map: tileTexture,
      roughness: 0.4,
      metalness: 0.6,
      bumpScale: 0.1,
    }),
  )
  suelo.rotation.x = -Math.PI / 2
  suelo.receiveShadow = true
  scene.add(suelo)

  // create references according to toggle
  if (mostrarReferenciasEspaciales.value) crearReferenciasEspaciales()

  // cargar modelo caja
  gltfLoader = new GLTFLoader()
  cargarModeloCaja().then(() => {
    renderizarCajas()
  })

  animate()
  // si el toggle ya estaba activo, iniciar streaming
  if (saveFrames.value) {
    frameStreamer.startStreaming(renderer, 10).catch((e) => console.error('FrameStreamer error:', e))
  }
  window.addEventListener('resize', onResize)
}

function animate() {
  animationId = requestAnimationFrame(animate)
  if (controls) controls.update()
  // aplicar movimiento WASD cuando la cámara está en modo libre
  if (controls && controls.enabled && camera) {
    const moveX = (keysPressed.d ? 1 : 0) - (keysPressed.a ? 1 : 0)
    const moveZ = (keysPressed.w ? 1 : 0) - (keysPressed.s ? 1 : 0)
    if (moveX !== 0 || moveZ !== 0) {
      const forward = new THREE.Vector3()
      camera.getWorldDirection(forward)
      forward.y = 0
      forward.normalize()

      const right = new THREE.Vector3()
      right.crossVectors(forward, camera.up).normalize()

    const delta = new THREE.Vector3()
    delta.copy(forward).multiplyScalar(moveZ * cameraWASDSpeed)
    delta.addScaledVector(right, moveX * cameraWASDSpeed)

    // Evitar salir del área cuando se mueve con WASD: calcular posición propuesta y clamarla
    const halfL = sueloLargo / 2
    const halfW = sueloAncho / 2
    const minY = 0.5
    const proposedPos = camera.position.clone().add(delta)
    proposedPos.x = Math.max(-halfL, Math.min(halfL, proposedPos.x))
    proposedPos.z = Math.max(-halfW, Math.min(halfW, proposedPos.z))
    proposedPos.y = Math.max(minY, proposedPos.y)

    const appliedDelta = proposedPos.clone().sub(camera.position)
    camera.position.add(appliedDelta)
    controls.target.add(appliedDelta)
    }
  }
  // actualizar posiciones de todos los tooltips para que siempre sean visibles
  if (cajasMesh.length) {
    cajasMesh.forEach((mesh) => {
      const id = mesh.userData?.caja?.id
      if (id != null) updateTooltipPositionForId(mesh, id)
    })
  }

  // restricciones camara libre
  if (controls && controls.enabled && camera) {
    const halfL = sueloLargo / 2
    const halfW = sueloAncho / 2
    // Relajar límites para permitir alejarse con la rueda del ratón
    const relaxFactor = 2.5
    const maxX = halfL * relaxFactor
    const maxZ = halfW * relaxFactor
    const minY = 0.3
    camera.position.x = Math.max(-maxX, Math.min(maxX, camera.position.x))
    camera.position.z = Math.max(-maxZ, Math.min(maxZ, camera.position.z))
    camera.position.y = Math.max(minY, camera.position.y)
    controls.target.x = Math.max(-maxX, Math.min(maxX, controls.target.x))
    controls.target.z = Math.max(-maxZ, Math.min(maxZ, controls.target.z))
  }

  renderer.render(scene, camera)
}

function downloadFrame() {
  if (!renderer) return
  renderer.domElement.toBlob(
    (blob) => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `frame-${Date.now()}.jpg`
      link.click()
      URL.revokeObjectURL(url)
    },
    'image/jpeg',
    0.95,
  )
}

// watch para enviar frames al servidor usando FrameStreamer
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

function onResize() {
  if (!container.value) return
  camera.aspect = container.value.clientWidth / container.value.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
}

// watch toggle para las referencias espaciales
watch(mostrarReferenciasEspaciales, (val) => {
  if (!scene) return
  if (val) crearReferenciasEspaciales()
  else limpiarReferenciasEspaciales()
})

// watch camera mode
watch(cameraMode, (mode) => {
  if (!camera) return
  if (!controls) return
  if (mode === 'libre') {
    controls.enabled = true
    return
  }
  controls.enabled = false
  camera.position.copy(posicionesCamara[mode])
  controls.update()
})

// watch para cambios en los props de simulacion
watch(
  () => props.simulacion,
  () => {
    renderizarCajas()
    syncScene()
  },
  { deep: true, immediate: true },
)

onMounted(init)

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onResize)
  controls?.dispose()
  limpiarReferenciasEspaciales()
  renderer?.dispose()
  // detener streaming al salir
  frameStreamer.stopStreaming()
  frameStreamer.disconnect()
  // limpiar listeners de teclado
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
})
</script>
