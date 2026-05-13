import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const CAMERA_SPEED = 0.12

export const POSICIONES_CAMARA = {
  libre: new THREE.Vector3(-0.2, 9.2, 9.2),
  frontal: new THREE.Vector3(-0.2, 9.2, 9.2),
  cenital: new THREE.Vector3(0, 20, 0.01),
}

export function initCameraControls(camera, renderer, initialMode) {
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.enabled = initialMode === 'libre'
  controls.enablePan = true
  controls.update()

  const keys = { w: false, a: false, s: false, d: false }

  function onKeyDown(e) {
    const k = (e.key || '').toLowerCase()
    if (k in keys) keys[k] = true
  }

  function onKeyUp(e) {
    const k = (e.key || '').toLowerCase()
    if (k in keys) keys[k] = false
  }

  function setMode(mode) {
    if (mode === 'libre') {
      controls.enabled = true
      return
    }
    controls.enabled = false
    camera.position.copy(POSICIONES_CAMARA[mode])
    controls.update()
  }

  function updateWASD() {
    if (!controls.enabled) return
    const moveX = (keys.d ? 1 : 0) - (keys.a ? 1 : 0)
    const moveZ = (keys.w ? 1 : 0) - (keys.s ? 1 : 0)
    if (moveX === 0 && moveZ === 0) return

    const forward = new THREE.Vector3()
    camera.getWorldDirection(forward)
    forward.y = 0
    forward.normalize()

    const right = new THREE.Vector3()
    right.crossVectors(forward, camera.up).normalize()

    const delta = new THREE.Vector3()
    delta.copy(forward).multiplyScalar(moveZ * CAMERA_SPEED)
    delta.addScaledVector(right, moveX * CAMERA_SPEED)

    camera.position.add(delta)
    controls.target.add(delta)
  }

  return { controls, onKeyDown, onKeyUp, setMode, updateWASD }
}
