<template>
  <div ref="container" class="scene"></div>

  <div>
    <div v-for="c in cajas" :key="c.id" class="tooltip" :style="getTooltipStyle(c.id)">
      <div class="tooltip-card">
        <div class="tooltip-header">
          <strong>Caja {{ c.id }}</strong>
          <div :class="['status-badge', c.abierta ? 'open' : 'closed']">
            {{ c.abierta ? 'Abierta' : 'Cerrada' }}
          </div>
        </div>
        <div class="tooltip-content">👥 {{ c.cola }} en cola</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, reactive, computed, watch } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const gtlfCajaPath = '/assets/3dmodels/psx_cashier_stand/scene.gltf'

const props = defineProps({
  cajas: {
    type: Array,
    default: () => [],
  },
})

const cajas = computed(() => props.cajas ?? [])

const sizeCaja = 1.5
const separacionCajas = 2.2 + sizeCaja
const cajasPorGrupo = 3
const espacioGrupos = 2.5

const sueloLargo = 40
const sueloAncho = 20

const mostrarReferenciasEspaciales = true

const camaraLibre = true

// const posicionCamara = new THREE.Vector3(0, 9, 18)
// const objetivoCamara = new THREE.Vector3(0, 0, 0)

// vista cenital para utilizar la camara como source de opencv
const posicionCamara = new THREE.Vector3(0, 20, 0)
const objetivoCamara = new THREE.Vector3(0, 0, 0)

const container = ref(null)
let scene, camera, renderer, animationId, gltfLoader, cajaModelo, controls
let referenciasEspaciales = []

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

  // elevar el tooltip unos pixels para que quede más arriba
  tooltipPositions[id].x = Math.round(x)
  tooltipPositions[id].y = Math.round(y) - 48
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
  const canvas = document.createElement('canvas')
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
  if (!scene || !mostrarReferenciasEspaciales) return

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

  const dependiente = crearCliente()
  dependiente.position.set(1, 0, 0)
  grupo.add(dependiente)
  if (!caja.abierta) dependiente.visible = false

  grupo.userData.dependiente = dependiente
  grupo.userData.clientes = []
  actualizarCola(grupo, caja.cola)
  return grupo
}

function crearClienteModelo() {
  const g = new THREE.Group()

  const cuerpo = new THREE.Mesh(
    new THREE.CylinderGeometry(0.28, 0.32, 1.0, 20),
    new THREE.MeshStandardMaterial({ color: Math.random() * 0xffffff }),
  )
  cuerpo.position.y = 0.5
  g.add(cuerpo)

  const cabeza = new THREE.Mesh(
    new THREE.SphereGeometry(0.22, 20, 20),
    new THREE.MeshStandardMaterial({ color: 0xf1c27d }),
  )
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

  return g
}

function crearClienteImagen() {}

function crearCliente() {
  return crearClienteModelo()
}

function actualizarCola(grupo, cantidad) {
  grupo.userData.clientes.forEach((c) => grupo.remove(c))
  grupo.userData.clientes = []

  for (let i = 0; i < cantidad; i++) {
    const cliente = crearCliente()
    cliente.position.set(1, 0, 2.5 + i * 1.25)
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
  console.log(cajas.value)

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
  camera.position.copy(posicionCamara)
  camera.lookAt(objetivoCamara)

  // render
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  container.value.appendChild(renderer.domElement)

  if (camaraLibre) {
    controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.target.copy(objetivoCamara)
    controls.update()
  }

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

  crearReferenciasEspaciales()

  // cargar modelo caja
  gltfLoader = new GLTFLoader()
  cargarModeloCaja().then(() => {
    renderizarCajas()
  })

  animate()
  window.addEventListener('resize', onResize)
}

function animate() {
  animationId = requestAnimationFrame(animate)
  if (controls) controls.update()
  // actualizar posiciones de todos los tooltips para que siempre sean visibles
  if (cajasMesh.length) {
    cajasMesh.forEach((mesh) => {
      const id = mesh.userData?.caja?.id
      if (id != null) updateTooltipPositionForId(mesh, id)
    })
  }
  renderer.render(scene, camera)
}

function onResize() {
  if (!container.value) return
  camera.aspect = container.value.clientWidth / container.value.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
}

watch(
  () => props.cajas,
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
})
</script>

<style scoped>
.scene {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.modal-top {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  justify-content: center;
  z-index: 20;
  pointer-events: none;
}

.modal {
  width: min(92vw, 420px);
  background: #ffffff;
  border-radius: 12px;
  padding: 0;
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.22);
  overflow: hidden;
  pointer-events: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.modal-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.status-badge {
  padding: 6px 14px;
  border-radius: 50px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.open {
  background: rgba(46, 204, 113, 0.9);
  color: white;
}

.status-badge.closed {
  background: rgba(231, 76, 60, 0.9);
  color: white;
}

.modal-content {
  padding: 20px 24px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 16px;
  color: #555;
  font-weight: 500;
}

.info-value {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  background: #f0f0f0;
  padding: 4px 12px;
  border-radius: 20px;
}

.tooltip {
  position: fixed;
  pointer-events: none;
}

.tooltip-card {
  background: #ffffff;
  border-radius: 10px;
  padding: 8px 12px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.16);
  display: inline-block;
  pointer-events: none;
}

.tooltip-header {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.tooltip-content {
  margin-top: 6px;
  font-weight: 600;
  color: #333;
}
</style>
