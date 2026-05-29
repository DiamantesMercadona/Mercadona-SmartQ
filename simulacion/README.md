# Simulación SmartQ

Simulación 3D de colas en cajas de supermercado, construida con Vue 3 + Three.js.

## Puesta en marcha

**1. Instalar dependencias**
```sh
npm install
```

**2. Configurar el entorno**

Renombra el fichero `example.env` a `.env`:
```sh
cp example.env .env
```
Ajusta las variables si el backend no corre en `localhost:8000`.

**3. Arrancar en desarrollo**
```sh
npm run dev
```

## Variables de la simulación

Los tiempos y parámetros que controlan el comportamiento de la simulación (frecuencia de llegada de clientes, tiempo de servicio en caja, velocidad inicial…) están centralizados en:

```
src/models/simulacionConfig.js
```

## Oleadas de clientes

Los clientes llegan a las cajas en **oleadas** periódicas. El comportamiento se controla con las siguientes variables en `src/models/simulacionConfig.js`:

| Variable | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `oleadasRandom` | `ref(bool)` | `false` | `true` → oleadas aleatorias, `false` → oleadas predefinidas |
| `oleadasLoop` | `ref(bool)` | `true` | Solo en modo predefinido: si `true`, el ciclo se reinicia al terminar el array |

### Modo aleatorio (`oleadasRandom = true`)

Cada oleada genera entre `MIN_CLIENTS_EVENT` y `MAX_CLIENTS_EVENT` clientes distribuidos en las cajas abiertas con menos cola. El intervalo entre oleadas es aleatorio entre `MIN_TIME_EVENT` y `MAX_TIME_EVENT` segundos.

### Modo predefinido (`oleadasRandom = false`)

Se recorre el array `oleadas` definido en `src/models/oleadas.js`. Cada entrada indica cuántos clientes llegan y cuántos segundos hay que esperar hasta la siguiente:

```js
{ clientes: 9, delay: 60 }
```

Cada cliente se asigna automáticamente a la caja abierta con menos cola. Si `oleadasLoop` es `false`, la simulación se detiene al terminar el array; si es `true`, vuelve a empezar desde la primera oleada.

Para añadir o modificar escenarios, edita directamente el array en `src/models/oleadas.js`.

### Factor de velocidad

Todos los tiempos (intervalo entre oleadas, tiempo de atención en caja) se dividen por el factor de velocidad global, ajustable con el slider del panel de controles (0.5×–20×).
