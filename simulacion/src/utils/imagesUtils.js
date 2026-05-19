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
  'alvaro.png',
  'alvaro2.png',
  // "jose.png",
]

const carrosArray = ['c1.png', 'c2.png', 'c3.png', 'c4.png', 'c5.png', 'c6.png']

const personasArray = [
  'p1.png',
  'p2.png',
  'p3.png',
  'p4.png',
  'p5.png',
  'p6.png',
  'p7.png',
  'p8.png',
  'p9.png',
  'p10.png',
  'p11.png',
]

let personaPrevIndex = -1

function getRandomFace() {
  const randomIndex = Math.floor(Math.random() * facesArray.length)
  return facesImgPath + facesArray[randomIndex]
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
  let randomIndex = -1
  do {
    randomIndex = Math.floor(Math.random() * personasArray.length)
  } while (personaPrevIndex === randomIndex)
  personaPrevIndex = randomIndex
  return personsImgPath + personasArray[randomIndex]
}

export { getRandomFace, getFacesRandomDependiente, getRandomCarrito, getRandomPersona }
