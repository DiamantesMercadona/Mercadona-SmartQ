import { reactive } from 'vue'
import Cliente from './Cliente.js'
import Dependiente from './Dependiente.js'
import { simulationSpeed } from './simulacionConfig.js'

class Caja {
  constructor(id) {
    this.id = id
    this.cola = reactive([])
    this.abierta = Math.random() < 0.5
    this.dependiente = this.abierta ? new Dependiente() : null
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
    const cliente = new Cliente(this.cola)
    this.cola.push(cliente)
    if (this.cola.length === 1) {
      this.removeClienteTimeout()
    }
    return cliente
  }

  removerCliente() {
    if (this.cola.length < 1) return null
    const clienteRemovido = this.cola.shift()
    return clienteRemovido
  }

  removeClienteTimeout() {
    if (this.cola.length == 0) return null
    const clienteTimeout = this.cola[0].tiempoEnCaja
    setTimeout(
      () => {
        this.removerCliente()
        this.removeClienteTimeout()
      },
      (clienteTimeout * 1000) / simulationSpeed.value,
    )
  }
}

export default Caja
