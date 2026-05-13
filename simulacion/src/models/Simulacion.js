import Caja from './Caja.js'

class Simulacion {
  constructor(n) {
    this.cajas = []
    this.generarCajas(n)
  }

  generarCajas(n) {
    for (let i = 0; i < n; i++) {
      this.cajas.push(new Caja(i))
    }
  }

  obtenerCaja(numeroCaja) {
    return this.cajas.find((caja) => caja.id === numeroCaja)
  }

  agregarCliente(numeroCaja) {
    const caja = this.obtenerCaja(numeroCaja)
    if (!caja) return null
    return caja.agregarCliente()
  }

  removerCliente(numeroCaja) {
    const caja = this.obtenerCaja(numeroCaja)
    if (!caja) return null
    return caja.removerCliente()
  }

  abrirCaja(numeroCaja) {
    const caja = this.obtenerCaja(numeroCaja)
    if (!caja) return null
    return caja.abrirCaja()
  }

  cerrarCaja(numeroCaja) {
    const caja = this.obtenerCaja(numeroCaja)
    if (!caja) return null
    caja.cerrarCaja()
  }
}

export default Simulacion
