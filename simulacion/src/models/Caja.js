import Cliente from './Cliente.js'

class Caja {
  constructor(id) {
    this.id = id
    this.cola = []
    const abierta = Math.random() < 0.5
    this.abierta = abierta
    if (abierta) {
      const nClientes = Math.floor(Math.random() * 5) + 1
      for (let i = 0; i < nClientes; i++) {
        this.cola.push(new Cliente())
      }
    }
  }
}

export default Caja
