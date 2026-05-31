# Guía de Uso - API del Backend

## Introducción

La API de Mercadona SmartQ (MSQ) es una interfaz HTTP y WebSocket de alto rendimiento construida sobre **FastAPI**. Actúa como el núcleo de comunicación bidireccional y persistencia entre:
* La **Simulación 3D interactiva** (que envía eventos de ocupación y transmisión de vídeo en tiempo real).
* El **Motor de Visión Artificial** (que procesa los frames de vídeo mediante YOLOv8).
* El **Motor de Decisiones** (que analiza las métricas de SLA y calcula desequilibrios).
* El **Frontend Dashboard** (el panel de control de gerencia que consume los datos para visualización).

---

## Estructura de la API y Enrutamiento

La API está dividida lógicamente en tres módulos de endpoints definidos en el subdirectorio `backend/api/`:
1. **GET Endpoints** (`get_endpoints.py`): Rutas de consulta rápida optimizadas para la lectura del panel de gerencia.
2. **POST/PATCH Endpoints** (`post_endpoints.py`): Rutas de mutación de datos y compatibilidad con el simulador, incluyendo autenticación y alertas.
3. **Video & WebSockets** (`video_endpoints.py`): Enrutador especializado en flujos binarios de alto rendimiento y canales de comunicación en tiempo real.

---

## Endpoints del Ecosistema

A continuación se detallan de forma exhaustiva los endpoints disponibles en el sistema con ejemplos prácticos de payloads.

### 1. Colas y Cajas

Gestión del inventario de líneas de cajas del supermercado y el estado de sus respectivas colas.

**`GET /api/v1/queues`**:
Retorna el estado de ocupación actual de todas las colas de las cajas registradoras.
* **Respuesta (200 OK)**:
```json
{
  "queues": [
    {
      "id": "1",
      "status": "abierta",
      "length": 3
    },
    {
      "id": "2",
      "status": "cerrada",
      "length": 0
    }
  ]
}
```

**`GET /api/v1/queues/{queue_id}`**:
Devuelve la información y longitud de una cola específica. Retorna `404 Not Found` si no existe la caja.

**`POST /api/v1/queues/{queue_id}`**:
Permite actualizar de forma remota la longitud y estado de una cola (utilizado por el simulador 3D para registrar cambios rápidos).
* **Cuerpo de la Solicitud (JSON)**:
```json
{
  "length": 4,
  "status": "abierta"
}
```

**`GET /api/v1/cajas`**:
Retorna la ficha del inventario de todas las cajas del supermercado, indicando qué empleado la tiene asignada.
* **Respuesta (200 OK)**:
```json
{
  "cajas": [
    {
      "id": "1",
      "estado": "abierta",
      "id_empleado": 3,
      "actualizado_en": "2026-05-29T23:00:00Z"
    }
  ]
}
```

**`POST /api/v1/cajas`**:
Crea de manera estática una nueva caja en la base de datos central.
* **Cuerpo de la Solicitud (JSON)**:
```json
{
  "id": "3",
  "estado": "cerrada",
  "id_empleado": null
}
```

**`PATCH /api/v1/cajas/{id_caja}`**:
Actualiza de forma parcial las propiedades de una caja activa (p. ej., asignar o desasignar empleados en tiempo real).
* **Cuerpo de la Solicitud (JSON)**:
```json
{
  "estado": "abierta",
  "id_empleado": 5
}
```

---

### 2. Histórico e Instantáneas

Almacena capturas temporales detalladas sobre la composición exacta de los clientes en las colas.

**`GET /api/v1/instantaneas`**:
Recupera el historial de instantáneas registradas por el motor de visión. Admite el parámetro de consulta `limite` para optimizar el tamaño de la respuesta.
* **Respuesta (200 OK)**:
```json
{
  "instantaneas": [
    {
      "id": 154,
      "capturada_en": "2026-05-29T23:15:30Z",
      "estado_cajas": {
        "1": ["sinCarro", "conCarro"],
        "2": ["sinCarro"]
      }
    }
  ]
}
```

**`POST /api/v1/instantaneas`**:
Registra una nueva instantánea detallada en el histórico. Es el punto de inyección de datos del motor de visión tras procesar cada fotograma.
* **Cuerpo de la Solicitud (JSON)**:
```json
{
  "estado_cajas": {
    "1": ["sinCarro", "sinCarro"],
    "3": ["conCarro"]
  }
}
```

---

### 3. Métricas y Rendimiento (SLA)

Métricas operativas de tiempos de espera calculadas por el procesador de decisiones.

**`GET /api/v1/metricas`**:
Retorna el historial de mediciones de tiempo de espera estimadas (SLA).
* **Parámetros de consulta (Query Params)**:
  * `id_caja` (opcional): Filtra métricas de una caja específica.
  * `solo_global` (opcional, boolean): Si es `true`, devuelve únicamente las métricas ponderadas generales del supermercado.
  * `desde` / `hasta` (opcionales): Rango de fechas en formato ISO8601.
  * `limite` (opcional, por defecto 10): Cantidad máxima de registros.
* **Respuesta (200 OK)**:
```json
{
  "metricas": [
    {
      "id": 859,
      "registrada_en": "2026-05-29T23:16:00Z",
      "id_caja": null,
      "tiempo_medio_espera_segundos": 4.85,
      "fuente": "decision_processor"
    }
  ]
}
```

**`POST /api/v1/metricas`**:
Registra un nuevo cálculo de KPI temporal.
* **Cuerpo de la Solicitud (JSON)**:
```json
{
  "tiempo_medio_espera_segundos": 6.2,
  "id_caja": "1",
  "fuente": "decision_processor"
}
```

---

### 4. Personal y Gestión de Turnos

Comprende la administración de la plantilla, asignación de dispositivos y la planificación semanal de horarios.

**`GET /api/v1/empleados`**:
Devuelve la lista completa de empleados. Soporta el parámetro opcional `activos=true` para listar únicamente a los empleados de alta.

**`POST /api/v1/empleados`**:
Da de alta a un nuevo empleado en el centro comercial, asignándole opcionalmente el identificador de su dispositivo pulsera.
* **Cuerpo de la Solicitud (JSON)**:
```json
{
  "nombre": "Carlos",
  "apellidos": "Sanz Ruiz",
  "id_pulsera": "p-958"
}
```

**`PATCH /api/v1/empleados/{id_empleado}`**:
Permite actualizar campos individuales de la ficha del empleado, o darlo de baja temporalmente (`activo: false`).

**`GET /api/v1/turnos`**:
Obtiene el cuadrante de asignación semanal completo (14 turnos repartidos entre mañana/tarde de lunes a domingo). Admite filtrar mediante `dia_semana` y `turno`.
* **Respuesta (200 OK)**:
```json
{
  "turnos": [
    {
      "id": 1,
      "dia_semana": "lunes",
      "turno": "mañana",
      "orden": [{"id": 3}, {"id": 12}],
      "actualizado_en": "2026-05-29T23:00:00Z"
    }
  ]
}
```

**`POST /api/v1/turnos`**:
Actualiza los empleados asignados a turnos concretos de la semana en formato de lote (UPSERT).
* **Cuerpo de la Solicitud (JSON)**:
```json
[
  {
    "dia_semana": "lunes",
    "turno": "mañana",
    "orden": [{"id": 3}, {"id": 12}]
  }
]
```

---



### 6. Video Ingestion & WebSockets de Tiempo Real

Canales de transmisión de flujos binarios y WebSockets bidireccionales optimizados de baja latencia.

**`GET /api/v1/redis/health`**:
Verifica de forma rápida el estado y conectividad contra el broker de Redis (o la simulación en memoria activa).
* **Respuesta (200 OK)**:
```json
{
  "redis": "ok",
  "channel": "msq:video:events",
  "connected": true
}
```

**`POST /api/v1/video/events`**:
Inyecta un payload binario en los canales rápidos de Redis.

**`WS /api/v1/ws/video`**:
Canal de WebSocket de entrada de flujos binarios. La simulación 3D interactiva se conecta aquí para transmitir a máxima velocidad los fotogramas JPEG capturados de la escena 3D WebGL. La API los recibe y los publica directamente al broker Pub/Sub.

**`WS /api/v1/ws/video/events`**:
Canal de WebSocket de salida. El Motor de Visión OpenCV se conecta a esta ruta para suscribirse en tiempo real a la transmisión de fotogramas, consumiendo de forma directa los bytes generados por la simulación.

**`POST /api/v1/pulsera/evento`**:
Envía y publica una alerta de vibración en Redis para ser retransmitida a los dispositivos inteligentes.
* **Cuerpo de la Solicitud (JSON)**:
```json
{
  "pulsera_id": "p-958",
  "evento": "abrir_caja"
}
```

**`WS /api/v1/ws/pulsera`**:
Canal de WebSocket donde se conectan los emuladores o dispositivos pulseras inteligentes de los empleados para recibir notificaciones de vibración en tiempo real.

**`POST /api/v1/display/evento`**:
Publica un mensaje de texto en Redis destinado a las pantallas digitales de las cajas.
* **Cuerpo de la Solicitud (JSON)**:
```json
{
  "mensaje": "Caja 3 cerrada. Por favor, vuelve a tu tarea asignada."
}
```

**`WS /api/v1/ws/display`**:
Canal de WebSocket donde las pantallas de caja se suscriben para escuchar y desplegar mensajes al cliente en tiempo real.
