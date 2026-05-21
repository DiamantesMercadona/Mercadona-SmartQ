import * as THREE from 'three'

export const CAMARA_POR_DEFECTO = 'frontal'

export const POSICIONES_CAMARA = {
  libre: {
    position: new THREE.Vector3(-0.02, 17.62, 10.13),
    lookAt: new THREE.Vector3(0.22, 0.0, -1.76),
  },
  frontal: {
    position: new THREE.Vector3(-0.34, 13.28, 14.83),
    lookAt: new THREE.Vector3(0.22, 0.0, -1.76),
  },
  frontal_2: {
    position: new THREE.Vector3(-0.02, 17.62, 10.13),
    lookAt: new THREE.Vector3(0.22, 0.0, -1.76),
  },
  cenital: {
    position: new THREE.Vector3(0.49, 26.94, 3.62),
    lookAt: new THREE.Vector3(0.53, 0.0, -1.77),
  },
}
