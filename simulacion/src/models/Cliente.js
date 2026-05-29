import { getRandomCarrito, getPersonaDistinta } from '@/utils/imagesUtils'
import {
  MIN_TIME_CAJA,
  MAX_TIME_CAJA,
  MIN_TIME_CAJA_CARRITO,
  MAX_TIME_CAJA_CARRITO,
  PROBABILIDAD_CARRITO,
} from './simulacionConfig.js'

class Cliente {
  constructor(colaActual = []) {
    this.id = `${Date.now()}-${Math.floor(Math.random() * 1000000)}`
    this.imagen = getPersonaDistinta(colaActual.map((c) => c.imagen))
    this.color = 0xffffff * Math.random()
    // this.imgCarrito = null
    this.imgCarrito =
      PROBABILIDAD_CARRITO > 0 && Math.random() < PROBABILIDAD_CARRITO ? getRandomCarrito() : null

    if (this.imgCarrito) {
      this.tiempoEnCaja =
        Math.floor(Math.random() * (MAX_TIME_CAJA_CARRITO - MIN_TIME_CAJA_CARRITO + 1)) +
        MIN_TIME_CAJA_CARRITO
    } else {
      this.tiempoEnCaja =
        Math.floor(Math.random() * (MAX_TIME_CAJA - MIN_TIME_CAJA + 1)) + MIN_TIME_CAJA
    }
  }
}

export default Cliente
