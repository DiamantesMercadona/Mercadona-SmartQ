import Caja from './Caja.js'
import {
  simulationSpeed,
  MIN_TIME_EVENT,
  MAX_TIME_EVENT,
  MIN_CLIENTS_EVENT,
  MAX_CLIENTS_EVENT,
} from './simulacionConfig.js'

class Simulacion {
  constructor(n) {
    this.cajas = []
    this.generarCajas(n)
    this.eventoSimulacion()
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

  seleccionarCaja() {
    const cajasAbiertas = this.cajas.filter((caja) => caja.abierta)
    if (cajasAbiertas.length === 0) return null
    // Seleccionar la caja con menos clientes
    const cajaSeleccionada = cajasAbiertas.reduce((prev, curr) =>
      prev.cola.length < curr.cola.length ? prev : curr,
    )
    return cajaSeleccionada.id
  }

  eventoSimulacion() {
    const n_clientes =
      Math.floor(Math.random() * (MAX_CLIENTS_EVENT - MIN_CLIENTS_EVENT + 1)) + MIN_CLIENTS_EVENT
    const tiempo_evento =
      Math.floor(Math.random() * (MAX_TIME_EVENT - MIN_TIME_EVENT + 1)) + MIN_TIME_EVENT
    console.log('Evento de simulación', { n_clientes, tiempo_evento })

    for (let i = 0; i < n_clientes; i++) {
      const numeroCaja = this.seleccionarCaja()
      if (numeroCaja !== null) {
        const c = this.agregarCliente(numeroCaja)
        console.log(
          `Cliente agregado a la caja ${numeroCaja} con tiempo en caja de ${c.tiempoEnCaja} segundos`,
        )
      }
    }

    setTimeout(
      () => {
        this.eventoSimulacion()
      },
      (tiempo_evento * 1000) / simulationSpeed.value,
    )
  }
}

export default Simulacion
