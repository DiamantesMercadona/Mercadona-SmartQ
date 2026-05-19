import Cliente from './Cliente.js'
import Dependiente from './Dependiente.js'

class Caja {
  constructor(id) {
    this.id = id
    this.cola = []
    this.abierta = Math.random() < 0.5
    this.dependiente = this.abierta ? new Dependiente() : null
    if (this.abierta) {
      const nClientes = Math.floor(Math.random() * 5) + 1
      for (let i = 0; i < nClientes; i++) {
        this.agregarCliente()
      }
    }
  }

  abrirCaja() {
    this.abierta = true
    if (!this.dependiente) {
      this.dependiente = new Dependiente()
    }
    return this.dependiente
  }

  cerrarCaja() {
    this.abierta = false
    this.dependiente = null
  }

  agregarCliente() {
    if (!this.abierta) return null
    const cliente = new Cliente()
    this.cola.push(cliente)
    return cliente
  }

  removerCliente() {
    if (this.cola.length < 1) return null

    const clienteRemovido = this.cola.shift()
    return clienteRemovido
  }
}

export default Caja
