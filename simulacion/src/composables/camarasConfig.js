import * as THREE from 'three'

export const CAMARA_POR_DEFECTO = 'frontal'

export const POSICIONES_CAMARA = {
  libre: {
    position: new THREE.Vector3(1.73, 15.96, 12.37),
    lookAt: new THREE.Vector3(2.02, 0.0, -1.67),
  },
  frontal: {
    position: new THREE.Vector3(1.73, 15.96, 12.37),
    lookAt: new THREE.Vector3(2.02, 0.0, -1.67),
  },
  cenital: {
    position: new THREE.Vector3(0.49, 26.94, 3.62),
    lookAt: new THREE.Vector3(0.53, 0.0, -1.77),
  },
}
