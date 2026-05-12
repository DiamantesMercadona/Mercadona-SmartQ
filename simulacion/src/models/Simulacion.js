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
}

export default Simulacion
