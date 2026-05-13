import { getRandomFace, getRandomCarrito } from '@/utils/imagesUtils'

class Cliente {
  id = Date.now()
  imagen = getRandomFace()
  color = 0xffffff * Math.random()
  imgCarrito = Math.random() < 0.35 ? getRandomCarrito() : null
}

export default Cliente
