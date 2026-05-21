import { getRandomCarrito, getPersonaDistinta } from '@/utils/imagesUtils'

class Cliente {
  constructor(colaActual = []) {
    this.id = `${Date.now()}-${Math.floor(Math.random() * 1000000)}`
    this.imagen = getPersonaDistinta(colaActual.map((c) => c.imagen))
    this.color = 0xffffff * Math.random()
    // this.imgCarrito = null
    this.imgCarrito = Math.random() < 0.35 ? getRandomCarrito() : null
  }
}

export default Cliente
