import { getRandomFace, getRandomCarrito, getRandomPersona } from '@/utils/imagesUtils'

class Cliente {
  id = `${Date.now()}-${Math.floor(Math.random() * 1000000)}`
  imagen = getRandomPersona()
  color = 0xffffff * Math.random()
  imgCarrito = Math.random() < 0.35 ? getRandomCarrito() : null
}

export default Cliente
