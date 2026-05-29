/** Array de oleadas de clientes.
 * Cada oleada es un objeto con:
 * - `clientes`: número de clientes que llegan en la oleada. Cada uno se asigna
 *   automáticamente a la caja abierta con menos cola.
 * - `delay`: segundos hasta la siguiente oleada (afectado por el factor de velocidad).
 */
export const oleadas = [
  { clientes: 9, delay: 60 },
  { clientes: 3, delay: 90 },
  { clientes: 7, delay: 75 },
  { clientes: 16, delay: 45 },
  { clientes: 4, delay: 120 },
]
