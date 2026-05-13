import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { getFacesRandomDependiente, getRandomPersona } from '@/utils/imagesUtils'

const GLTF_CAJA_PATH = '/assets/3dmodels/psx_cashier_stand/scene.gltf'
const SIZE_CAJA = 1.5
const SEPARACION_CAJAS = 3.5 + SIZE_CAJA
const CAJAS_POR_GRUPO = 3
const ESPACIO_GRUPOS = 2.5
const FACE_SCALE = 0.75
const CARRITO_SCALE = 2.3
const CARRITO_POSITION = new THREE.Vector3(1.5, -0.5, 0)

export function cargarModeloCaja() {
  return new Promise((resolve) => {
    const loader = new GLTFLoader()
    loader.load(GLTF_CAJA_PATH, (gltf) => {
      const modelo = gltf.scene
      modelo.scale.set(SIZE_CAJA, SIZE_CAJA, SIZE_CAJA)
      resolve(modelo)
    })
  })
}

function crearCarrito(imgCarrito) {
  const g = new THREE.Group()
  const tex = new THREE.TextureLoader().load(imgCarrito)
  tex.colorSpace = THREE.SRGBColorSpace
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: tex, transparent: true, alphaTest: 0.18, color: 0xd6d6d6 }),
  )
  sprite.scale.set(CARRITO_SCALE, CARRITO_SCALE, 1)
  g.add(sprite)
  return g
}

export function crearDependiente(data = {}) {
  const g = new THREE.Group()
  const loader = new THREE.TextureLoader()

  const cuerpo = new THREE.Mesh(
    new THREE.CylinderGeometry(0.28, 0.32, 1.0, 20),
    new THREE.MeshStandardMaterial({ color: data.color ?? 0x3b82f6 }),
  )
  cuerpo.position.y = 0.5
  g.add(cuerpo)

  const faceTex = loader.load(data.imagen || getFacesRandomDependiente())
  faceTex.colorSpace = THREE.SRGBColorSpace
  const cabeza = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: faceTex, transparent: true, alphaTest: 0.18, color: 0xd6d6d6 }),
  )
  cabeza.scale.set(FACE_SCALE, FACE_SCALE, 1)
  cabeza.position.y = 1.25
  g.add(cabeza)

  const brazoMat = new THREE.MeshStandardMaterial({ color: 0xf1c27d })
  const brazoGeo = new THREE.BoxGeometry(0.12, 0.55, 0.12)
  const brazoIzq = new THREE.Mesh(brazoGeo, brazoMat)
  brazoIzq.position.set(-0.35, 0.7, 0)
  g.add(brazoIzq)
  const brazoDer = brazoIzq.clone()
  brazoDer.position.x = 0.35
  g.add(brazoDer)

  return g
}

export function crearCliente(data) {
  const g = new THREE.Group()
  const tex = new THREE.TextureLoader().load(data.imagen || getRandomPersona())
  tex.colorSpace = THREE.SRGBColorSpace
  const persona = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: tex, transparent: true, alphaTest: 0.18, color: 0xd6d6d6 }),
  )
  persona.scale.set(2.5, 3.5, 1)
  g.add(persona)

  if (data.imgCarrito != null) {
    const carrito = crearCarrito(data.imgCarrito)
    carrito.position.copy(CARRITO_POSITION)
    g.add(carrito)
  }

  return g
}

export function actualizarCola(grupo, cola) {
  grupo.userData.clientes.forEach((c) => grupo.remove(c))
  grupo.userData.clientes = []
  if (!cola || cola.length < 1) return
  for (let i = 0; i < cola.length; i++) {
    const cliente = crearCliente(cola[i])
    const zigzag = i % 2 === 0 ? -0.35 : 0.35
    const offsetX =
      1.2 +
      zigzag +
      Math.sin(i * 1.1) * 0.45 +
      Math.cos(i * 0.65) * 0.25 +
      (Math.random() - 0.5) * 0.6
    const offsetZ = 2.35 + i * 1.15 + Math.sin(i * 0.85) * 0.5 + (Math.random() - 0.5) * 0.65
    cliente.position.set(offsetX, 1.5, offsetZ)
    grupo.add(cliente)
    grupo.userData.clientes.push(cliente)
  }
}

function crearCajaGrupo(caja, x, cajaModelo) {
  const grupo = new THREE.Group()
  grupo.position.set(x, 0, -7)
  grupo.userData.caja = caja
  grupo.userData.clientes = []

  grupo.add(cajaModelo.clone())

  if (caja.dependiente) {
    const dep = crearDependiente(caja.dependiente)
    dep.position.set(1, 0, 0)
    grupo.add(dep)
    grupo.userData.dependiente = dep
  } else {
    grupo.userData.dependiente = null
  }

  actualizarCola(grupo, caja.cola)
  return grupo
}

export function limpiarCajasEscena(scene, cajasMesh) {
  cajasMesh.forEach((m) => scene.remove(m))
  cajasMesh.length = 0
}

export function renderizarCajas(scene, cajas, cajaModelo, cajasMesh, onInitTooltip) {
  if (!scene || !cajaModelo) return
  limpiarCajasEscena(scene, cajasMesh)

  const posX = cajas.map((_, i) => {
    const g = Math.floor(i / CAJAS_POR_GRUPO)
    return (i - (cajas.length - 1) / 2) * (SEPARACION_CAJAS + 0.5) + g * ESPACIO_GRUPOS
  })
  const centroX = posX.length ? (Math.min(...posX) + Math.max(...posX)) / 2 : 0

  cajas.forEach((caja, i) => {
    const grupo = crearCajaGrupo(caja, posX[i] - centroX, cajaModelo)
    cajasMesh.push(grupo)
    scene.add(grupo)
    onInitTooltip(caja.id)
  })
}

export function syncScene(cajas, cajasMesh) {
  cajas.forEach((caja, i) => {
    const grupo = cajasMesh[i]
    if (!grupo) return
    actualizarCola(grupo, caja.cola)

    const depActual = grupo.userData.dependiente
    if (caja.dependiente && !depActual) {
      const dep = crearDependiente(caja.dependiente)
      dep.position.set(1, 0, 0)
      grupo.add(dep)
      grupo.userData.dependiente = dep
    } else if (!caja.dependiente && depActual) {
      grupo.remove(depActual)
      grupo.userData.dependiente = null
    }
  })
}
