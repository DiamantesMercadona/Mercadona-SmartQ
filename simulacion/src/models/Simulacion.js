import Caja from './Caja.js'
import { getCajas, getQueues } from '../services/backendApi.js'
import {
  simulationSpeed,
  MIN_TIME_EVENT,
  MAX_TIME_EVENT,
  MIN_CLIENTS_EVENT,
  MAX_CLIENTS_EVENT,
} from './simulacionConfig.js'

/** El backend usa 'activa' para caja abierta y 'cerrada' para caja cerrada. */
const STATUS_ABIERTA = ['activa', 'abierta'] // añado 'Abierta' por si acaso.

class Simulacion {
  async inicializar() {
    this.cajas = []
    try {
      // getQueues incluye `length` (nº de clientes) calculado desde la última instantánea
      const queues = await getQueues()
      for (const q of queues) {
        const caja = new Caja(q.id, {
          abierta: STATUS_ABIERTA.includes(q.status),
          colaLength: q.length ?? 0,
        })
        this.cajas.push(caja)
      }
      console.log(`[Simulacion] ${queues.length} cajas cargadas desde el backend`)
    } catch (error) {
      console.error('[Simulacion] Error al obtener el estado inicial:', error)
    }
    // Delay inicial para que los primeros clientes no lleguen inmediatamente al iniciar la simulación
    setTimeout(() => this.eventoSimulacion(), 1000)
  }

  async refrescarEstadoCajas() {
    const cajas = await getCajas()
    for (const c of cajas) {
      const caja = this.obtenerCaja(c.id)
      if (!caja) continue
      caja.abierta = STATUS_ABIERTA.includes(c.estado)
      caja.sincronizarDependiente(caja.abierta)
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

  async abrirCaja(numeroCaja) {
    const caja = this.obtenerCaja(numeroCaja)
    if (!caja) return null
    return caja.abrirCaja()
  }

  async cerrarCaja(numeroCaja) {
    const caja = this.obtenerCaja(numeroCaja)
    if (!caja) return null
    return caja.cerrarCaja()
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
