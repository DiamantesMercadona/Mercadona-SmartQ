import * as THREE from 'three'

export function crearFondoEscena() {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 512
  const ctx = canvas.getContext('2d')
  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height)
  gradient.addColorStop(0, '#1a1a2e')
  gradient.addColorStop(0.5, '#16213e')
  gradient.addColorStop(1, '#0f3460')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  return new THREE.CanvasTexture(canvas)
}

export function crearSuelo(sueloLargo, sueloAncho) {
  const c = document.createElement('canvas')
  c.width = 512
  c.height = 512
  const ctx = c.getContext('2d')

  ctx.fillStyle = '#d6d2c4'
  ctx.fillRect(0, 0, c.width, c.height)

  const tileSize = 128
  ctx.strokeStyle = 'rgba(120,110,100,0.35)'
  ctx.lineWidth = 3
  for (let x = 0; x <= c.width; x += tileSize) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, c.height)
    ctx.stroke()
  }
  for (let y = 0; y <= c.height; y += tileSize) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(c.width, y)
    ctx.stroke()
  }

  ctx.fillStyle = 'rgba(255,255,255,0.1)'
  for (let x = 0; x < c.width; x += tileSize) {
    for (let y = 0; y < c.height; y += tileSize) {
      ctx.fillRect(x + 5, y + 5, tileSize - 10, tileSize - 10)
    }
  }

  const tex = new THREE.CanvasTexture(c)
  tex.wrapS = THREE.RepeatWrapping
  tex.wrapT = THREE.RepeatWrapping
  tex.repeat.set(6, 4)

  return new THREE.Mesh(
    new THREE.PlaneGeometry(sueloLargo, sueloAncho),
    new THREE.MeshStandardMaterial({
      map: tex,
      roughness: 0.35,
      metalness: 0.12,
      color: 0xd6d2c4,
    }),
  )
}

export function crearLuces(scene, sueloLargo) {
  const ambient = new THREE.AmbientLight(0xfff8f0, 1.0)
  scene.add(ambient)

  const dir = new THREE.DirectionalLight(0xfff5e0, 0.9)
  dir.position.set(8, 16, 8)
  dir.castShadow = true
  scene.add(dir)

  // Fluorescent ceiling spotlights (supermarket style)
  const xPositions = [-sueloLargo / 4, 0, sueloLargo / 4]
  xPositions.forEach((x) => {
    const spot = new THREE.PointLight(0xfff8e7, 0.55, 24)
    spot.position.set(x, 8, -3)
    scene.add(spot)
  })
}
