import { reactive } from 'vue'
import Cliente from './Cliente.js'
import Dependiente from './Dependiente.js'
import { simulationSpeed } from './simulacionConfig.js'
import { patchCajaEstado } from '../services/backendApi.js'

class Caja {
  /**
   * @param {number} id
   * @param {boolean} abierta
   * @param {number} colaLength
   */
  constructor(id, abierta = false, colaLength = 0) {
    this.id = id
    this.cola = reactive([])
    this.abierta = abierta
    this.dependiente = this.abierta ? new Dependiente() : null

    // Poblar la cola con el número de clientes indicado por el backend
    for (let i = 0; i < colaLength; i++) {
      const cliente = new Cliente(this.cola)
      this.cola.push(cliente)
    }
    if (this.cola.length > 0) {
      this.removeClienteTimeout()
    }
  }

  /** Actualiza el estado local y persiste el cambio en el backend. */
  async abrirCaja() {
    this.abierta = true
    if (!this.dependiente) {
      this.dependiente = new Dependiente()
    }
    try {
      await patchCajaEstado(this.id, 'activa')
    } catch (e) {
      console.warn(`[Caja ${this.id}] No se pudo actualizar el backend:`, e.message)
    }
    return this.dependiente
  }

  /** Actualiza el estado local y persiste el cambio en el backend. */
  async cerrarCaja() {
    this.abierta = false
    this.dependiente = null
    try {
      await patchCajaEstado(this.id, 'cerrada')
    } catch (e) {
      console.warn(`[Caja ${this.id}] No se pudo actualizar el backend:`, e.message)
    }
  }

  sincronizarDependiente(abierta) {
    this.dependiente = abierta ? new Dependiente() : null
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
