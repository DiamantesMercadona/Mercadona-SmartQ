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

## Base de Datos

La base de datos `queues.db` se crea automáticamente con datos de ejemplo al iniciar la aplicación.