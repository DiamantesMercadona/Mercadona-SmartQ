# Mercadona Queue API

Esta API proporciona acceso al estado de las colas de Mercadona desde una base de datos SQLite.

## Estructura

- `main.py`: Archivo principal de la aplicación FastAPI.
- `database.py`: Funciones para interactuar con la base de datos SQLite.
- `get_endpoints.py`: Endpoints GET para obtener el estado de las colas.
- `post_endpoints.py`: Endpoints POST para actualizar el estado de las colas.
- `__init__.py`: Archivo para hacer que `api` sea un paquete Python.

## Instalación

1. Instalar dependencias: `pip install -r requirements.txt`
2. Ejecutar la API: `python api/main.py`

La API estará disponible en `http://localhost:8000`.

## Endpoints

### GET /api/v1/queues
Obtiene el estado de todas las colas.

Respuesta:
```json
{
  "queues": [
    {
      "id": 1,
      "name": "Caja 1",
      "length": 5,
      "status": "activa"
    },
    ...
  ]
}
```

### GET /api/v1/queues/{queue_id}
Obtiene el estado de una cola específica.

### POST /api/v1/queues/{queue_id}
Actualiza el estado de una cola.

Cuerpo de la solicitud:
```json
{
  "length": 10,
  "status": "activa"
}
```

### GET /api/v1/redis/health
Comprueba si la API puede conectarse a Redis y muestra el canal Pub/Sub usado.

### POST /api/v1/video/events
Recibe una medicion del simulador/camara y la publica en Redis.

Cuerpo de la solicitud:
```json
{
  "camera_id": "simulador-3d",
  "zone": "Caja_1",
  "frame_id": 1,
  "people_count": 5,
  "metadata": {
    "fps": 30
  }
}
```

El evento se publica en el canal configurado como `msq:video:events`.

### WS /api/v1/ws/video
WebSocket para recibir eventos continuos del simulador y reenviarlos a Redis.
El cliente debe enviar frames binarios. La API publica esos bytes en Redis y
responde con un ACK tambien binario.

### GET /api/v1/video/events/latest
Devuelve el ultimo evento de video guardado en Redis como `application/octet-stream`.

### WS /api/v1/ws/video/events
WebSocket de salida para la parte derecha del sistema. La API se suscribe al
canal Redis `msq:video:events` y reenvia cada evento a los clientes como bytes.

## Base de Datos

La base de datos `queues.db` se crea automáticamente con datos de ejemplo al iniciar la aplicación.
