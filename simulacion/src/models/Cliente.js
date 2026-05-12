import { getRandomFace } from '@/utils/imagesUtils'

class Cliente {
  id = Date.now()
  imagen = getRandomFace()
  color = 0xffffff * Math.random()

  usaCarrito = Math.random() < 0.35
}

export default Cliente
