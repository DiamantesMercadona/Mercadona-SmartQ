import { ref } from 'vue'

// CAMBIAR VALORES CUANDO EL SLISDER DE VELOCIDAD FUNCIONE CORECTAMENTE (aplicart a los setTimeout ya creados, no solo a los nuevos)
// posibilidad de simplemente dejar como esta y ponser el slider por defecto a 20 o un valor más alto.

//  Velocidad global

/** Factor de velocidad de la simulación (slider hasta 20x). */
export const simulationSpeed = ref(10)

//  Comportamiento de colas

/** Si es true, al abrir una caja los clientes en espera se redistribuyen equitativamente. */
export const nivelarColasAlAbrir = ref(true)

//  Oleadas de llegada

/** Segundos entre cada oleada de nuevos clientes. */
export const MIN_TIME_EVENT = 60
export const MAX_TIME_EVENT = 120

/** Clientes que llegan por oleada. */
export const MIN_CLIENTS_EVENT = 1
export const MAX_CLIENTS_EVENT = 4

//  Tiempo de servicio en caja

/** Cesta pequeña (sin carrito): 2–4 min. */
export const MIN_TIME_CAJA = 120
export const MAX_TIME_CAJA = 240

/** Carrito completo: 5–10 min. */
export const MIN_TIME_CAJA_CARRITO = 300
export const MAX_TIME_CAJA_CARRITO = 600
