# Guía de Uso - Simulación 3D

## Introducción

La simulación 3D de Mercadona SmartQ (MSQ) es un entorno interactivo construido con **Vue 3** y **Three.js (WebGL)**. Modela el comportamiento físico de los clientes, las cintas transportadoras y las colas de las 6 cajas registradoras. 

Esta simulación actúa como la fuente de vídeo y eventos del sistema, capturando y transmitiendo fotogramas JPEG comprimidos a través de WebSockets hacia el backend para que sean procesados por el motor de visión y analizados por el algoritmo de toma de decisiones.

---

## Parámetros de Configuración

Todos los tiempos, velocidades y límites físicos que gobiernan la simulación 3D están centralizados en un único archivo de configuración reactiva:

```
simulacion/src/models/simulacionConfig.js
```

Modificando las variables de este archivo se puede alterar el rendimiento, el comportamiento de las cajas y la velocidad de atención al cliente.

---

## Ingesta y Oleadas de Clientes

Los clientes entran al supermercado y se dirigen automáticamente a la caja abierta que tenga la **cola más corta en ese momento**. El flujo de entrada se organiza en **oleadas** periódicas gobernadas por dos variables principales:

| Variable | Tipo | Valor por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `oleadasRandom` | `Ref<boolean>` | `false` | `true` para generar oleadas aleatorias; `false` para usar una secuencia predefinida. |
| `oleadasLoop` | `Ref<boolean>` | `true` | Si es `true`, la secuencia de oleadas predefinidas se reiniciará en bucle infinito al terminar. |

### 1. Modo Aleatorio (`oleadasRandom = true`)
Cada cierto tiempo aleatorio (comprendido entre `MIN_TIME_EVENT` y `MAX_TIME_EVENT` segundos), se genera una nueva oleada de clientes. 
* El número de clientes generados por oleada es un entero aleatorio entre `MIN_CLIENTS_EVENT` y `MAX_CLIENTS_EVENT`.

### 2. Modo Predefinido (`oleadasRandom = false`)
Recorre de forma secuencial una planificación fija declarada en el archivo:

```
simulacion/src/models/oleadas.js
```

Cada elemento de la planificación representa un evento de llegada con su respectivo retraso en segundos hasta el siguiente evento:

* **Ejemplo de Estructura de Oleada**:
```javascript
{
  clientes: 9,  // Cantidad de personas que entran de golpe
  delay: 60     // Segundos de espera hasta la siguiente oleada
}
```

> **Consejo**: Para diseñar o reproducir escenarios de estrés o flujos de clientes específicos (p. ej., hora punta simulada), edita directamente la lista del archivo `oleadas.js`.

---

## Factores de Simulación

### Control de Velocidad Temporal
El panel de controles del frontend incluye un deslizador (*slider*) que permite acelerar o ralentizar la simulación desde **0.5×** hasta **20×** de la velocidad en tiempo real:
* Todos los tiempos internos (el intervalo de espera entre oleadas, la velocidad de movimiento de los avatares y el tiempo de atención de las cajeras) se dividen automáticamente por el factor de velocidad seleccionado, agilizando las pruebas de saturación.

### Captura y Envío de Video
Para que el motor de visión (OpenCV + YOLOv8) pueda recibir los fotogramas en directo, debes asegurarte de que la opción **"Enviar Video / Frames"** está marcada en la interfaz de la simulación. Esto inicia la captura del buffer WebGL y su transmisión por WebSocket.
