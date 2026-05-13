import * as THREE from 'three'

function crearEtiquetaEje(texto, color) {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 128
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.font = 'bold 64px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.strokeStyle = '#ffffff'
  ctx.lineWidth = 10
  ctx.strokeText(texto, canvas.width / 2, canvas.height / 2)
  ctx.fillStyle = color
  ctx.fillText(texto, canvas.width / 2, canvas.height / 2)
  const tex = new THREE.CanvasTexture(canvas)
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }))
  sprite.scale.set(0.9, 0.45, 1)
  return sprite
}

export function useReferenciasEspaciales(sueloLargo, sueloAncho) {
  let refs = []

  function crear(scene) {
    limpiar(scene)

    const margen = 1.25
    const esquina = new THREE.Vector3(-sueloLargo / 2 + margen, 0.05, -sueloAncho / 2 + margen)

    const ejes = new THREE.AxesHelper(2)
    ejes.position.copy(esquina)
    scene.add(ejes)
    refs.push(ejes)
    ;[
      { texto: 'X', color: '#ef4444', offset: new THREE.Vector3(2.25, 0.12, 0) },
      { texto: 'Y', color: '#22c55e', offset: new THREE.Vector3(0, 2.15, 0) },
      { texto: 'Z', color: '#3b82f6', offset: new THREE.Vector3(0, 0.12, 2.25) },
    ].forEach(({ texto, color, offset }) => {
      const label = crearEtiquetaEje(texto, color)
      label.position.copy(esquina).add(offset)
      scene.add(label)
      refs.push(label)
    })

    const centro = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 16, 16),
      new THREE.MeshStandardMaterial({
        color: 0xffffff,
        emissive: 0xffffff,
        emissiveIntensity: 0.7,
      }),
    )
    centro.position.set(0, 0.12, 0)
    scene.add(centro)
    refs.push(centro)

    const grid = new THREE.GridHelper(sueloLargo, sueloLargo, 0x9ca3af, 0x4b5563)
    grid.position.y = 0.01
    scene.add(grid)
    refs.push(grid)
  }

  function limpiar(scene) {
    refs.forEach((obj) => scene.remove(obj))
    refs = []
  }

  return { crear, limpiar }
}
