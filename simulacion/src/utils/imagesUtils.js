const personsImgPath = '/assets/imagenes/faces/'
const carritoImgPath = '/assets/imagenes/carritos/'

const imagenCarrito = carritoImgPath + 'carrito.png'

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
]

function getRandomFace() {
  const randomIndex = Math.floor(Math.random() * facesArray.length)
  return personsImgPath + facesArray[randomIndex]
}

function getAlvaroFace() {
  return personsImgPath + 'alvaro.png'
}

export { getRandomFace, getAlvaroFace, imagenCarrito }
