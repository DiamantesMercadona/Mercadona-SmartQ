# Guía de Uso - Base de Datos

## Introducción

`DatabaseMSQ` es el gestor centralizado de base de datos SQLite, que proporciona un acceso unificado y tipado a todas las entidades del sistema: instantáneas, cajas, métricas, empleados, usuarios y turnos.

---

## Esquema canónico

La base de datos se organiza en varias tablas clave para almacenar la información necesaria para el funcionamiento del sistema. A continuación se describen las tablas principales y su estructura:

### **1. instantaneas**
Registro histórico de muestras (instantáneas) del estado de todas las cajas en ciertos momentos dados.

```
id, capturada_en, estado_cajas
```

Ejemplo de instantanea:
```json
{
  "capturada_en": "2026-05-18T10:30:00Z",
  "estado_cajas": {
    "1": ["sinCarro", "conCarro", "sinCarro"],
    "2": ["sinCarro"]
  }
}
```

### **2. cajas**
Información sobre las cajas disponibles, su estado de ocupación y el empleado que las ocupa.

```
id, estado, id_empleado, actualizado_en
```

Ejemplo de caja:
```json
{
  "id": "1",
  "estado": "abierta",
  "id_empleado": 5,
  "actualizado_en": "2026-05-18T10:30:00Z"
}
```

### **3. metricas**
Serie temporal de tiempo medio de espera, tanto global como por caja.

```
id, registrada_en, id_caja, tiempo_medio_espera_segundos, fuente
```

Ejemplo de métrica global:
```json
{
    
    "id": 1,
    "registrada_en": "2026-05-18T10:30:00Z",
    "id_caja": null,
    "tiempo_medio_espera_segundos": 4.5,
    "fuente": "decision_processor"
}
```

Ejemplo de métrica por caja:
```json
{
    "id": 2,
    "registrada_en": "2026-05-18T10:30:00Z",
    "id_caja": "Caja_1",
    "tiempo_medio_espera_segundos": 5.2,
    "fuente": "decision_processor"
}
```

La tabla se usa para registrar puntos temporales y consultarlos con filtros por caja, rango temporal y límite de resultados.

### **4. empleados**
Registro de empleados del centro.

```
id, nombre, apellidos, id_pulsera, activo, creado_en, actualizado_en
```

Ejemplo de empleado:
```json
{
    "id": 1,
    "nombre": "Juan",
    "apellidos": "García López",
    "id_pulsera": "001",
    "activo": true,
    "creado_en": "2026-05-18T10:00:00Z",
    "actualizado_en": "2026-05-18T10:30:00Z"
}
```

### **5. usuarios**
Usuarios para autenticación en el frontend.

```
id, usuario, password_hash, activo, creado_en, actualizado_en
```

Ejemplo de usuario:
```json
{
    "id": 1,
    "usuario": "admin",
    "password_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d154",
    "activo": true,
    "creado_en": "2026-05-18T09:00:00Z",
    "actualizado_en": "2026-05-18T09:00:00Z"
}
```

> **Importante:** Al inicializar la base de datos por primera vez, el sistema creará automáticamente un usuario administrador predeterminado si la tabla está vacía. Sus credenciales de acceso iniciales serán **usuario**: `admin`, **contraseña**: `1234`. Se recomienda cambiar esta contraseña posteriormente o dar de alta un usuario definitivo.

### **6. turnos**
Programación semanal de empleados por día y franja.

```
id, dia_semana, turno, orden_json, actualizado_en
```

Ejemplo de turno:
```json
{
    "id": 1,
    "dia_semana": "lunes",
    "turno": "mañana",
    "orden_json": [
        {"id": 3},
        {"id": 10},
        {"id": 18}
    ],
    "actualizado_en": "2026-05-18T10:30:00Z"
}
```

Los turnos vacíos se guardan como listas vacías (`[]`) para indicar que esa franja no requiere empleados.

> **Importante:** Al inicializar la base de datos por primera vez (o al crearse el esquema `turnos`), el sistema generará automáticamente de forma preventiva entradas para todos los días de la semana (`lunes` a `domingo`) y ambos turnos (`mañana` y `tarde`) con listas vacías `[]`, asegurando que las consultas a la semana nunca devuelvan errores por registros faltantes.

---

## Como usar la clase `DatabaseMSQ`

### Instalación y Configuración

1. **Importar la clase:**
   ```python
   from backend.database import DatabaseMSQ
   ```

2. **Crear una instancia:**
   ```python
   # Opción 1: Con context manager (RECOMENDADO)
   with DatabaseMSQ() as db:
       # ... usar db ...
       # Se cierra automáticamente

   # Opción 2: Sin context manager (requiere cerrar manualmente)
   db = DatabaseMSQ()
   # ... usar db ...
   db.close()
   ```

3. **Ubicación de la BD:**
   - Ruta por defecto (recomendada): definida en `CONFIG["DATABASE"]["db_path"]` (en `config.py`).
   - Ruta personalizada durante la instanciación (no recomendada): `DatabaseMSQ(db_path="/ruta/custom.db")`.

---

## Ejemplos prácticos por funcionalidad

A continuación se muestran ejemplos de uso para todos los métodos públicos disponibles.

### 1. Instantáneas

La principal forma de almacenar la ocupación actual observada por el motor de visión y crear el histórico.

**`registrar_instantanea`**:
Registra el estado actual de todas las cajas (personas o grupos de persona con carro vs sin carro). Esto sirve de entrada para los cálculos de tiempos medios de espera y para el análisis de saturación.
```python
with DatabaseMSQ() as db:
    snapshot_id = db.registrar_instantanea(
        estado_cajas={
            "1": ["sinCarro", "conCarro", "sinCarro"],
            "2": ["sinCarro"]
        }
    )
```

**`obtener_instantaneas`**:
Retorna los últimos eventos almacenados (por defecto hasta 10). Se utiliza mayormente desde el Motor de Decisiones para analizar tendencias de cola y aplicar regresiones.
```python
with DatabaseMSQ() as db:
    snapshots = db.obtener_instantaneas(limite=5)
    for s in snapshots:
        print(s["capturada_en"], s["estado_cajas"])
```

---

### 2. Cajas

Gestión del inventario de cajas en la tienda, si están habilitadas y qué empleado (si lo hay) está trabajando en cada una.

**`crear_caja`**:
Da de alta una nueva caja en la base de datos de manera estática.
```python
with DatabaseMSQ() as db:
    db.crear_caja(id="1", estado="cerrada", id_empleado=None)
```

**`eliminar_caja`**:
Elimina de forma física una caja existente en base a su ID.
```python
with DatabaseMSQ() as db:
    exito = db.eliminar_caja(id="1")
```

**`actualizar_caja`**:
Modifica los datos de una caja existente.
> **Patrón `_UNSET`**: Los parámetros se omitan en la llamada a esra función, no se sobrescribirán con nulos; se quedarán tal cual. Para asignar explícitamente el valor `None` (por ejemplo, para desasignar un empleado), se debe indicar expresamente (`id_empleado=None`).
```python
from backend.database import _UNSET

with DatabaseMSQ() as db:
    # Actualizar solo el estado
    db.actualizar_caja(id="1", estado="abierta")
    
    # Asignar un empleado
    db.actualizar_caja(id="1", id_empleado=5)
    
    # Desasignar el empleado explícitamente y cerrar la caja
    db.actualizar_caja(id="1", estado="cerrada", id_empleado=None)
```

**`obtener_caja`**:
Devuelve un diccionario con el detalle actual (estado y empleado) de la caja individual requerida.
```python
with DatabaseMSQ() as db:
    caja = db.obtener_caja(id="1")
    if caja:
        print(caja["id"], caja["estado"], caja["id_empleado"])
```

**`obtener_cajas`**:
Carga la lista completa con el estado detallado de todas las cajas. Retorna siempre una lista (pre-ordenada por ID de caja).
```python
with DatabaseMSQ() as db:
    todas_las_cajas = db.obtener_cajas()
```

---

### 3. Métricas

Monitorización de los Tiempos de Carga/Espera y KPIs registrados.

**`registrar_metrica`**:
Guarda un valor (tiempo o estimación) calculado de procedencia conocida.
> **Métricas globales**: Es posible emitir una métrica *Global* (si no se especifica el ID de la caja) indicando el promedio global, o una métrica local indicando la situación en tiempo de espera asociada concretamente a un ID de caja.
```python
with DatabaseMSQ() as db:
    # Métrica global
    db.registrar_metrica(tiempo_medio_espera_segundos=4.5, fuente="decision_processor")
    
    # Métrica de una caja específica
    db.registrar_metrica(
        tiempo_medio_espera_segundos=5.2,
        id_caja="1",
        fuente="decision_processor"
    )
```

**`obtener_metricas`**:
Búsqueda multi-filtro de los KPIs con limitador por defecto (últimos 10 resultados). Soporta encadenar filtros por `id_caja`, un lapso de tiempo `desde`-`hasta` (formato ISO8601), y poder segmentar para listar `solo_global`.
```python
with DatabaseMSQ() as db:
    metricas = db.obtener_metricas(
        id_caja="1",
        desde="2026-05-17T00:00:00Z",
        hasta="2026-05-18T00:00:00Z",
        limite=50
    )
```

---

### 4. Empleados

Tabla principal de datos sobre el personal, sus IDs, sus correspondientes dispositivos IoT y si están o no de alta laboral.

**`crear_empleado`**:
Registra en empleado en la base de datos devolviendo la clave única `id` del empleado nuevo.
```python
with DatabaseMSQ() as db:
    emp_id = db.crear_empleado(nombre="Juan", apellidos="García López", id_pulsera="001")
```

**`listar_empleados`**:
Devuelve a parte/toda la plantilla bajo la particularidad de poder usar su parámetro opcional `activos=True` para descartar en la query a quienes estén de baja (por defecto devuelve todo).
```python
with DatabaseMSQ() as db:
    # Solo los empleados activos
    empleados_activos = db.listar_empleados(activos=True)
```

**`obtener_empleado`**:
Devuelve la ficha de un único empleado.
```python
with DatabaseMSQ() as db:
    emp = db.obtener_empleado(id_empleado=1)
```

**`actualizar_empleado`**:
Actualiza ciertos campos de un empleado sin perder los demás, implementando el mismo patrón `_UNSET` idéntico al de las cajas. Es posible cambiar el nombre o activar/desactivar el boolean de `activo`.
```python
with DatabaseMSQ() as db:
    db.actualizar_empleado(id_empleado=1, nombre="Juan", activo=False)
```

**`eliminar_empleado`**:
Borrado físico estricto. Devolverá `True` o `False` si logra efectuar el borrado. Para un borrado "blando" se deberá emplear el previo `actualizar_empleado` indicando `activo=False`.
```python
with DatabaseMSQ() as db:
    exito = db.eliminar_empleado(id_empleado=1)
```

---

### 5. Usuarios (Frontend)

Comprende las credenciales privadas y encriptadas de los administradores que acceden a la interfaz de gestión.

**`crear_usuario`**:
Crea un usuario mediante la generación interna de hash criptográfico estándar (SHA-256). Nunca se guarda en texto claro la contraseña proporcionada de entrada.
```python
with DatabaseMSQ() as db:
    user_id = db.crear_usuario(usuario="admin", contraseña="MiPassword123")
```

**`autenticar_usuario`**:
Verifica las credenciales evaluando ambos hashes de comparación. Si coinciden, devuelve la instancia del objeto usuario desde SQLite (y sin su password), validando así la sesión para el frontend, y en caso contrario, se devuelve `None`.
```python
with DatabaseMSQ() as db:
    user = db.autenticar_usuario(usuario="admin", contraseña="MiPassword123")
    if user:
        print("Autenticación exitosa")
```

**`eliminar_usuario`**:
Revoca permanentemente y borra la cuenta de un usuario.
```python
with DatabaseMSQ() as db:
    exito = db.eliminar_usuario(id_usuario=1)
```

---

### 6. Turnos

Determina con días de la semana y periodos (mañanas/tardes) la preferencia de las aperturas de cajas. Las casillas del cuadrante que estén conformadas por un diccionario sin empleados en su lista, indicará turno deshabitado.

**`actualizar_turnos`**:
Permite insertar turnos individuales o en lote mediante un array estructurado (lista de dicccionarios), admitiendo la cláusula de sobrescritura UPSERT.
> **Particularidad**: Es posible proporcionar un solo bloque con el Turno (p. ej un Lunes tarde modificado) o todo un lote de múltiples cambios. El método resolverá un bucle y persistirá el cambio completo.
```python
with DatabaseMSQ() as db:
    # Se puede modificar un turno o varios al mismo tiempo
    db.actualizar_turnos([
        {"dia_semana": "lunes", "turno": "mañana", "orden": [{"id": 3}, {"id": 10}]},
        {"dia_semana": "lunes", "turno": "tarde", "orden": []}
    ])
```

**`obtener_turnos`**:
Obtiene toda la semana de turnos o un subconjunto específico, listo para iterar. Se pueden aplicar filtros opcionales por `dia_semana` y `turno` para recuperar solo el bloque deseado.
>Si es llamado vacío de parámetros, devuelve `14 elementos`, es decir, el cuadrante integral de toda la semana estipulada de lunes a domingo.
```python
with DatabaseMSQ() as db:
    # Obtener toda la semana
    semana = db.obtener_turnos()
    
    # Obtener un turno específico
    lunes_manana = db.obtener_turnos(dia_semana="lunes", turno="mañana")
```

---

## Cierre de Conexiones

**Cerrar la base de datos explícitamente (cuando no se está utilizando context manager):**
```python
db = DatabaseMSQ()
try:
    db.registrar_instantanea({"Caja_1": ["sinCarro", "sinCarro", "sinCarro"]})
finally:
    db.close()
```