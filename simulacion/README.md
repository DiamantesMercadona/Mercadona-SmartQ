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
