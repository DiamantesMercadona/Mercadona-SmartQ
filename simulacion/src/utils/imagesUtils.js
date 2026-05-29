const facesImgPath = '/assets/imagenes/faces/'
const personsImgPath = '/assets/imagenes/personas/'
const carritoImgPath = '/assets/imagenes/carritos/'

const facesArray = [
  '60b26b0ee6c7580004508998.png',
  '60b26b2ce6c7580004508999.png',
  '60b26b47e6c758000450899a.png',
  '60b26b5ee6c758000450899b.png',
  '60b26b8ee6c758000450899c.png',
  '60b26c78e6c758000450899f.png',
  '60b26cb7e6c75800045089a0.png',
  '60b26de3e6c75800045089a2.png',
  '60b26f18e6c75800045089a4.png',
  '60b270ffe6c75800045089a5.png',
  // 'alvaro.png',
  // 'alvaro2.png',
]

const carrosArray = ['c1.png', 'c2.png', 'c3.png', 'c4.png', 'c5.png', 'c6.png']

// shirtColor: color dominante de la camiseta en RGB [r, g, b]
const personasArray = [
  { file: 'p1.png', shirtColor: [212, 192, 168] },
  { file: 'p2.png', shirtColor: [218, 220, 228] },
  { file: 'p3.png', shirtColor: [180, 165, 140] },
  { file: 'p4.png', shirtColor: [128, 126, 122] },
  { file: 'p5.png', shirtColor: [82, 55, 38] },
  { file: 'p6.png', shirtColor: [52, 50, 48] },
  { file: 'p7.png', shirtColor: [72, 98, 148] },
  { file: 'p8.png', shirtColor: [232, 178, 22] },
  { file: 'p9.png', shirtColor: [38, 90, 195] },
  { file: 'p10.png', shirtColor: [205, 138, 28] },
  { file: 'p11.png', shirtColor: [122, 120, 118] },
]

function colorDist([r1, g1, b1], [r2, g2, b2]) {
  return Math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)
}

function getFacesRandomDependiente() {
  const randomIndex = Math.floor(Math.random() * facesArray.length)
  return facesImgPath + facesArray[randomIndex]
}

function getRandomCarrito() {
  const randomIndex = Math.floor(Math.random() * carrosArray.length)
  return carritoImgPath + carrosArray[randomIndex]
}

function getRandomPersona() {
  const randomIndex = Math.floor(Math.random() * personasArray.length)
  return personsImgPath + personasArray[randomIndex].file
}

// Elige la imagen con el color de camiseta más distinto respecto a los ya presentes en cola.
// usadasPaths: array de rutas de imagen ya asignadas a clientes en la cola.
function getPersonaDistinta(usadasPaths = []) {
  const usadasColors = usadasPaths
    .map((path) => {
      const file = path.split('/').pop()
      return personasArray.find((p) => p.file === file)?.shirtColor
    })
    .filter(Boolean)

  if (usadasColors.length === 0) return getRandomPersona()

  const candidatas = personasArray.filter((p) => !usadasPaths.includes(personsImgPath + p.file))
  const pool = candidatas.length > 0 ? candidatas : personasArray

  let bestScore = -1
  let mejores = []
  for (const entry of pool) {
    const minDist = Math.min(...usadasColors.map((c) => colorDist(entry.shirtColor, c)))
    if (minDist > bestScore) {
      bestScore = minDist
      mejores = [entry]
    } else if (minDist === bestScore) {
      mejores.push(entry)
    }
  }

  const best = mejores[Math.floor(Math.random() * mejores.length)]
  return personsImgPath + best.file
}

export { getFacesRandomDependiente, getRandomCarrito, getRandomPersona, getPersonaDistinta }
