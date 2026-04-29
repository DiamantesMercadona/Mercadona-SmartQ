<template>
  <div ref="container" class="scene"></div>
  <div>
    <button @click="actualizarCajas">TEST</button>
  </div>

  <div v-if="selectedCaja" class="modal-top">
    <div class="modal">
      <div class="modal-header">
        <h2>Caja {{ selectedCaja.id }}</h2>
        <div :class="['status-badge', selectedCaja.abierta ? 'open' : 'closed']">
          {{ selectedCaja.abierta ? 'Abierta' : 'Cerrada' }}
        </div>
      </div>
      <div class="modal-content">
        <div class="info-row">
          <span class="info-label">👥 Personas en cola:</span>
          <span class="info-value">{{ selectedCaja.cola }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, reactive, computed } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

const gtlfCajaPath = '/assets/3dmodels/psx_cashier_stand/scene.gltf'

const sizeCaja = 1.5
const separacionCajas = 2.2 + sizeCaja

// temporal, estatico
const numCajas = ref(5)

const container = ref(null)
let scene, camera, renderer, animationId, gltfLoader, cajaModelo
const raycaster = new THREE.Raycaster()
const pointer = new THREE.Vector2()

const cajas = reactive([])
const cajasMesh = []
const selectedCaja = ref(null)

// temporal, genera cajas aleatorias
function generarCajas() {
  cajas.length = 0
  for (let i = 0; i < numCajas.value; i++) {
    const abierta = Math.random() > 0.35
    cajas.push({
      id: i + 1,
      abierta: abierta,
      cola: abierta ? Math.floor(Math.random() * 6) : 0,
    })
  }
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

function crearCaja(caja, x) {
  const grupo = new THREE.Group()
  grupo.position.x = x
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

function crearCliente() {
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

function actualizarCola(grupo, cantidad) {
  grupo.userData.clientes.forEach((c) => grupo.remove(c))
  grupo.userData.clientes = []

  for (let i = 0; i < cantidad; i++) {
    const cliente = crearCliente()
    cliente.position.set(1, 0, 2 + i * 1.25)
    grupo.add(cliente)
    grupo.userData.clientes.push(cliente)
  }
}

function syncScene() {
  cajas.forEach((caja, i) => {
    actualizarCola(cajasMesh[i], caja.cola)
    cajasMesh[i].userData.dependiente.visible = caja.abierta
  })
}

function init() {
  const sueloLargo = 28
  const sueloAncho = 18
  generarCajas()

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
  camera.position.set(0, 9, 18)
  camera.lookAt(0, 0, 0)

  // render y hovers
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  container.value.appendChild(renderer.domElement)
  renderer.domElement.addEventListener('pointermove', onHoverScene)
  renderer.domElement.addEventListener('pointerleave', onLeaveScene)

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

  // cargar modelo caja
  gltfLoader = new GLTFLoader()
  cargarModeloCaja().then(() => {
    cajas.forEach((caja, i) => {
      const x = (i - (numCajas.value - 1) / 2) * (separacionCajas + 0.5)
      const modelo = crearCaja(caja, x)
      cajasMesh.push(modelo)
      scene.add(modelo)
    })
  })

  animate()
  window.addEventListener('resize', onResize)
}

function animate() {
  animationId = requestAnimationFrame(animate)
  renderer.render(scene, camera)
}

function onResize() {
  if (!container.value) return
  camera.aspect = container.value.clientWidth / container.value.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
}

function buscarCajaDesdeObjeto(obj) {
  let actual = obj
  while (actual) {
    if (actual.userData?.caja) return actual.userData.caja
    actual = actual.parent
  }
  return null
}

function onHoverScene(event) {
  if (!renderer || !camera || cajasMesh.length === 0) return

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)
  const intersects = raycaster.intersectObjects(cajasMesh, true)
  if (!intersects.length) {
    selectedCaja.value = null
    return
  }

  const caja = buscarCajaDesdeObjeto(intersects[0].object)
  if (!caja) {
    selectedCaja.value = null
    return
  }
  selectedCaja.value = cajas.find((c) => c.id === caja.id) || null
}

function onLeaveScene() {
  selectedCaja.value = null
}

onMounted(init)

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onResize)
  renderer?.domElement?.removeEventListener('pointermove', onHoverScene)
  renderer?.domElement?.removeEventListener('pointerleave', onLeaveScene)
  renderer?.dispose()
})

// para probar cambios en tiempo real, luego esto vendra del backend
function actualizarCajas() {
  generarCajas()
  syncScene()
}
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
</style>
