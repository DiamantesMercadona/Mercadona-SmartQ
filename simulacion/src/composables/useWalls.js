import * as THREE from 'three'

const MERCADONA_GREEN = '#009A44'
const WALL_HEIGHT = 8

function texturaParedLateral() {
  const c = document.createElement('canvas')
  c.width = 512
  c.height = 512
  const ctx = c.getContext('2d')

  ctx.fillStyle = '#eeeae2'
  ctx.fillRect(0, 0, c.width, c.height)

  ctx.strokeStyle = 'rgba(160,150,135,0.3)'
  ctx.lineWidth = 2
  for (let x = 0; x <= c.width; x += 128) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, c.height)
    ctx.stroke()
  }
  for (let y = 0; y <= c.height; y += 128) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(c.width, y)
    ctx.stroke()
  }

  // Green skirting board
  ctx.fillStyle = MERCADONA_GREEN
  ctx.fillRect(0, c.height * 0.87, c.width, c.height)

  return new THREE.CanvasTexture(c)
}

async function texturaParedFondo(canvasW, canvasH) {
  const logo = await new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => resolve(null)
    img.src = '/assets/logo_mercadona.png'
  })

  const c = document.createElement('canvas')
  c.width = canvasW
  c.height = canvasH
  const ctx = c.getContext('2d')

  ctx.fillStyle = '#eeeae2'
  ctx.fillRect(0, 0, c.width, c.height)

  ctx.strokeStyle = 'rgba(160,150,135,0.3)'
  ctx.lineWidth = 2
  const tile = Math.round(c.width / 32)
  for (let x = 0; x <= c.width; x += tile) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, c.height)
    ctx.stroke()
  }
  for (let y = 0; y <= c.height; y += tile) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(c.width, y)
    ctx.stroke()
  }

  // Green central band
  const bY = Math.round(c.height * 0.28)
  const bH = Math.round(c.height * 0.4)
  ctx.fillStyle = MERCADONA_GREEN
  ctx.fillRect(0, bY, c.width, bH)

  // Band highlight edges
  ctx.fillStyle = 'rgba(255,255,255,0.15)'
  ctx.fillRect(0, bY, c.width, 5)
  ctx.fillRect(0, bY + bH - 5, c.width, 5)

  // Logo + MERCADONA text centered together
  const fontSize = Math.round(c.height * 0.25)
  ctx.font = `bold ${fontSize}px Arial, Helvetica, sans-serif`
  const textWidth = ctx.measureText('MERCADONA').width
  const bandCenterY = bY + bH / 2

  const logoH = logo ? Math.round(bH * 0.65) : 0
  const logoW = logo ? Math.round(logo.width * (logoH / logo.height)) : 0
  const gap = logo ? Math.round(fontSize * 0.35) : 0
  const totalW = logoW + gap + textWidth
  const startX = (c.width - totalW) / 2

  if (logo) {
    ctx.drawImage(logo, startX, bandCenterY - logoH / 2, logoW, logoH)
  }

  ctx.fillStyle = '#ffffff'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText('MERCADONA', startX + logoW + gap, bandCenterY)

  // Green skirting board
  ctx.fillStyle = MERCADONA_GREEN
  ctx.fillRect(0, Math.round(c.height * 0.87), c.width, c.height)

  return new THREE.CanvasTexture(c)
}

export async function crearParedes(scene, sueloLargo, sueloAncho) {
  const texFondo = await texturaParedFondo(2048, 512)
  const matFondo = new THREE.MeshStandardMaterial({
    map: texFondo,
    roughness: 0.82,
    metalness: 0.0,
  })

  const paredFondo = new THREE.Mesh(new THREE.PlaneGeometry(sueloLargo, WALL_HEIGHT), matFondo)
  paredFondo.position.set(0, WALL_HEIGHT / 2, -sueloAncho / 2)
  scene.add(paredFondo)

  const texLateral = texturaParedLateral()
  texLateral.wrapS = THREE.RepeatWrapping
  texLateral.wrapT = THREE.RepeatWrapping
  texLateral.repeat.set(2, 1)
  const matLateral = new THREE.MeshStandardMaterial({
    map: texLateral,
    roughness: 0.82,
    metalness: 0.0,
  })

  const paredIzq = new THREE.Mesh(new THREE.PlaneGeometry(sueloAncho, WALL_HEIGHT), matLateral)
  paredIzq.position.set(-sueloLargo / 2, WALL_HEIGHT / 2, 0)
  paredIzq.rotation.y = Math.PI / 2
  scene.add(paredIzq)

  const texLateralDer = texturaParedLateral()
  texLateralDer.wrapS = THREE.RepeatWrapping
  texLateralDer.wrapT = THREE.RepeatWrapping
  texLateralDer.repeat.set(2, 1)
  const matLateralDer = new THREE.MeshStandardMaterial({
    map: texLateralDer,
    roughness: 0.82,
    metalness: 0.0,
  })

  const paredDer = new THREE.Mesh(new THREE.PlaneGeometry(sueloAncho, WALL_HEIGHT), matLateralDer)
  paredDer.position.set(sueloLargo / 2, WALL_HEIGHT / 2, 0)
  paredDer.rotation.y = -Math.PI / 2
  scene.add(paredDer)
}
