import { ref } from 'vue'

// CAMBIAR VALORES CUANDO EL SLISDER DE VELOCIDAD FUNCIONE CORECTAMENTE (aplicart a los setTimeout ya creados, no solo a los nuevos)
// posibilidad de simplemente dejar como esta y ponser el slider por defecto a 20 o un valor más alto.

//  Velocidad global

/** Factor de velocidad de la simulación (slider hasta 20x). */
export const simulationSpeed = ref(1)

//  Oleadas de llegada

/** Segundos entre cada oleada de nuevos clientes. */
export const MIN_TIME_EVENT = 10 //60
export const MAX_TIME_EVENT = 20 //120

/** Clientes que llegan por oleada. */
export const MIN_CLIENTS_EVENT = 1
export const MAX_CLIENTS_EVENT = 4

//  Tiempo de servicio en caja

/** Cesta pequeña (sin carrito): 2–4 min. */
export const MIN_TIME_CAJA = 10 // 120
export const MAX_TIME_CAJA = 20 // 240

/** Carrito completo: 5–10 min. */
export const MIN_TIME_CAJA_CARRITO = 15 // 300
export const MAX_TIME_CAJA_CARRITO = 25 // 600
