# Importaciones y configuración
from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from config import CONFIG

# Valor especial para indicar que un argumento no se ha proporcionado, permitiendo distinguir entre "no modificar" y "establecer a None".
_UNSET = object()

# Declara la la clase DatabaseMSQ, que proporciona una interfaz unificada para todas las operaciones de base de datos necesarias en el sistema.
class DatabaseMSQ:
    """
    Gestor centralizado de la base de datos SQLite.

    Proporciona acceso unificado a todas las tablas del esquema canónico, incluyendo:
    - instantáneas del estado de cajas (instantaneas)
    - cajas y su estado (cajas)
    - métricas operativas (metricas)
    - empleados (empleados)
    - turnos y órdenes de turno (turnos)
    """

    # Métodos públicos de inicialización y gestión de conexión
    def __init__(self, db_path: Optional[str] = None):
        """Inicializa la conexión a la base de datos.

        Crea automáticamente todas las tablas del esquema canónico si no existen.
        Las conexiones deben cerrarse con .close() o usarse con context manager (with).

        Args:
            db_path: Ruta al archivo SQLite. Si es None, usa CONFIG["DATABASE"]["db_path"].

        Example:
            # Sin context manager
            db = DatabaseMSQ()
            db.registrar_instantanea({"1": ["sinCarro", "sinCarro", "conCarro"]})
            db.close()

            # Con context manager (recomendado)
            with DatabaseMSQ() as db:
                db.registrar_instantanea({"1": ["sinCarro", "sinCarro", "conCarro"]})
        """
        self.db_path = db_path or CONFIG["DATABASE"]["db_path"]
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        self._initialize_schema()

    # ------------------------------------------------------------------
    # Inicialización del esquema y utilidades de bajo nivel
    # ------------------------------------------------------------------

    # Define el esquema de la base de datos, creando las tablas necesarias si no existen.
    def _initialize_schema(self) -> None:
        self._create_tabla_instantaneas()
        self._create_tabla_cajas()
        self._create_tabla_metricas()
        self._create_tabla_empleados()
        self.cursor.execute("DROP TABLE IF EXISTS usuarios")
        self.conn.commit()
        self._ensure_default_empleados()
        self._create_tabla_turnos()
        self._ensure_default_turnos()

    # Permite convertir estructuras de datos a JSON para almacenamiento, manejando casos de None.
    def _json_dumps(self, payload: Any) -> Optional[str]:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    # Permite cargar un JSON desde la base de datos, manejando casos de NULL o cadena vacía.
    def _json_loads(self, payload: Optional[str]) -> Any:
        if payload in (None, ""):
            return None
        return json.loads(payload)

    # Convierte una fila de resultado de SQLite a un diccionario con nombres de columnas como claves.
    def _row_to_dict(self, row: sqlite3.Row | Tuple[Any, ...], columns: Sequence[str]) -> Dict[str, Any]:
        return {column: row[index] for index, column in enumerate(columns)}



    # Devuelve la fecha/hora actual en formato ISO 8601, para uso consistente en timestamps.
    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # Crea la tabla de instantáneas, que almacena el estado de las cajas en momentos específicos.
    def _create_tabla_instantaneas(self) -> None:
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS instantaneas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capturada_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                estado_cajas TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    # Crea la tabla de cajas, que almacena el estado actual de cada caja y el empleado asignado.

    def _create_tabla_cajas(self) -> None:
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cajas (
                id TEXT PRIMARY KEY,
                estado TEXT NOT NULL,
                id_empleado INTEGER,
                actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_empleado) REFERENCES empleados(id) ON DELETE SET NULL
            )
            """
        )
        self.conn.commit()

    # Crea la tabla de métricas, que almacena mediciones de tiempo medio de espera, asociadas opcionalmente a una caja concreta.
    def _create_tabla_metricas(self) -> None:
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metricas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registrada_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                id_caja TEXT,
                tiempo_medio_espera_segundos REAL NOT NULL,
                fuente TEXT NOT NULL DEFAULT 'decision_processor',
                FOREIGN KEY (id_caja) REFERENCES cajas(id) ON DELETE SET NULL
            )
            """
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_metricas_caja_fecha ON metricas (id_caja, registrada_en)"
        )
        self.conn.commit()

    # Crea la tabla de empleados, que almacena información sobre los empleados y las pulseras IoT asociadas.
    def _create_tabla_empleados(self) -> None:
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS empleados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                apellidos TEXT NOT NULL,
                id_pulsera TEXT UNIQUE,
                activo INTEGER NOT NULL DEFAULT 1,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()



    # Asegura que existan los 6 empleados de base con nombres valencianos si la tabla está vacía.
    def _ensure_default_empleados(self) -> None:
        # Omitir la siembra de datos si estamos en un entorno de pruebas unitarias o memoria
        import sys
        if (
            ":memory:" in self.db_path 
            or "test" in self.db_path 
            or any("unittest" in arg or "test" in arg for arg in sys.argv)
            or "unittest" in sys.modules
        ):
            return

        self.cursor.execute("SELECT COUNT(*) FROM empleados")
        if self.cursor.fetchone()[0] == 0:
            empleados = [
                ("Vicent", "Climent Ortiz", "P-001"),
                ("Amparo", "Fuster Martí", "P-002"),
                ("Josep", "Balaguer Sifre", "P-003"),
                ("Neus", "Soler Gadea", "P-004"),
                ("Xavi", "Sanchis Barberá", "P-005"),
                ("Mireia", "Llopis Sendra", "P-006")
            ]
            now = self._now_iso()
            records = [
                (nom, ape, pul, 1, now, now)
                for nom, ape, pul in empleados
            ]
            self.cursor.executemany(
                """
                INSERT INTO empleados (nombre, apellidos, id_pulsera, activo, creado_en, actualizado_en)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                records
            )
            self.conn.commit()

    # Crea la tabla de turnos, que almacena la organización de turnos y precedencia de empleados para cada día y turno.
    def _create_tabla_turnos(self) -> None:
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS turnos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_semana TEXT NOT NULL,
                turno TEXT NOT NULL,
                orden_json TEXT NOT NULL,
                actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(dia_semana, turno)
            )
            """
        )
        self.conn.commit()

    # Asegura que la tabla de turnos tenga una configuración base (vacía) para todos los días y turnos si está vacía.
    def _ensure_default_turnos(self) -> None:
        self.cursor.execute("SELECT COUNT(*) FROM turnos")
        if self.cursor.fetchone()[0] == 0:
            dias = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
            turnos = ["mañana", "tarde"]
            now = self._now_iso()
            records = [
                (dia, turno, "[]", now)
                for dia in dias
                for turno in turnos
            ]
            self.cursor.executemany(
                """
                INSERT INTO turnos (dia_semana, turno, orden_json, actualizado_en)
                VALUES (?, ?, ?, ?)
                """,
                records
            )
            self.conn.commit()

    # ------------------------------------------------------------------
    # Registro y consulta de instantáneas
    # ------------------------------------------------------------------

    # Método para registrar una instantánea completa del estado de las cajas, con un timestamp automático.
    def registrar_instantanea(
        self,
        estado_cajas: Dict[str, Any],
    ) -> int:
        """Registra una instantánea completa del estado de las cajas.

        Registra una muestra ordenada del estado de cada caja en un momento.

        Args:
            estado_cajas: Dict con `id` (caja) como clave y lista ordenada de grupos.
                Ej: {"1": ["sinCarro", "conCarro", "sinCarro"], "2": ["sinCarro"]}

        Returns:
            ID de la instantánea registrada.

        Example:
            with DatabaseMSQ() as db:
                snapshot_id = db.registrar_instantanea(
                    estado_cajas={
                        "1": ["sinCarro", "conCarro", "sinCarro"],
                        "2": ["sinCarro"]
                    }
                )
                print(f"Instantánea guardada: {snapshot_id}")
        """
        self.cursor.execute(
            """
            INSERT INTO instantaneas (
                capturada_en,
                estado_cajas
            ) VALUES (?, ?)
            """,
            (
                self._now_iso(),
                self._json_dumps(estado_cajas) or "{}",
            ),
        )
        self.conn.commit()
        return int(self.cursor.lastrowid)

    # Método para obtener las N instantáneas más recientes del estado de las cajas, con filtros opcionales.
    def obtener_instantaneas(self, limite: int = 10) -> List[Dict[str, Any]]:
        """Obtiene las N instantáneas más recientes del estado de cajas.

        Args:
            limite: Número máximo de instantáneas a devolver. Si es menor que 1, retorna una lista vacía.

        Returns:
            Lista de dicts con los datos de cada instantánea (id, capturada_en, estado_cajas),
            ordenada de la más reciente a la más antigua.

        Example:
            with DatabaseMSQ() as db:
                ultimas = db.obtener_instantaneas(5)
                for snapshot in ultimas:
                    print(snapshot["capturada_en"])
        """
        if limite < 1:
            return []

        self.cursor.execute(
            """
            SELECT id, capturada_en, estado_cajas
            FROM instantaneas
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite,),
        )
        rows = self.cursor.fetchall()
        return [
            {
                "id": row[0],
                "capturada_en": row[1],
                "estado_cajas": self._json_loads(row[2]) or {},
            }
            for row in rows
        ]
    
    # ------------------------------------------------------------------
    # Registro, consulta y actualización de cajas
    # ------------------------------------------------------------------

    # Método para crear una nueva caja en la base de datos, con estado inicial y empleado asignado opcionalmente.
    def crear_caja(
        self,
        id: str,
        estado: str,
        id_empleado: Optional[int] = None,
    ) -> None:
        """Añade una caja nueva a la base de datos.

        Args:
            id: Identificador único de la caja (ej: "1", "Caja_Principal").
            estado: Estado inicial de la caja ("abierta", "cerrada", etc.).
            id_empleado: ID del empleado asignado a la caja (opcional).

        Example:
            with DatabaseMSQ() as db:
                db.crear_caja(id="1", estado="cerrada", id_empleado=None)
        """
        if estado == "activa":
            estado = "abierta"

        # Si la caja se abre, asignar automáticamente un empleado libre si no tiene uno
        if estado == "abierta" and id_empleado is None:
            self.cursor.execute("SELECT id FROM empleados WHERE activo = 1")
            todos_empleados = [r[0] for r in self.cursor.fetchall()]
            
            self.cursor.execute("SELECT id_empleado FROM cajas WHERE estado IN ('abierta', 'activa') AND id_empleado IS NOT NULL")
            empleados_ocupados = [r[0] for r in self.cursor.fetchall()]
            
            empleados_libres = [e for e in todos_empleados if e not in empleados_ocupados]
            if empleados_libres:
                id_empleado = empleados_libres[0]

        self.cursor.execute(
            """
            INSERT INTO cajas (id, estado, id_empleado, actualizado_en)
            VALUES (?, ?, ?, ?)
            """,
            (id, estado, id_empleado, self._now_iso()),
        )
        self.conn.commit()

    # Método para eliminar una caja de la base de datos, identificada por su ID.
    def eliminar_caja(self, id: str) -> bool:
        """Elimina una caja de la base de datos.

        Args:
            id: Identificador único de la caja.

        Returns:
            True si la caja existía y se eliminó, False en caso contrario.
        """
        self.cursor.execute("DELETE FROM cajas WHERE id = ?", (id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    # Método para actualizar el estado y/o empleado asignado de una caja existente, identificada por su ID.
    def actualizar_caja(
        self,
        id: str,
        estado: Optional[str] = None,
        id_empleado: Any = _UNSET,
    ) -> bool:
        """Actualiza una caja existente.

        Args:
            id: Identificador único de la caja.
            estado: Nuevo estado de la caja. Si es None, no se modifica.
            id_empleado: Nuevo empleado asignado. Usa None para desasignar la caja;
                omite el argumento para no modificarlo.

        Returns:
            True si la caja existía y se actualizó, False si no hubo cambios o no existía.
        """
        # Si la caja se cierra, desasignar automáticamente el empleado si no se ha especificado otra cosa
        if estado == "cerrada" and id_empleado is _UNSET:
            id_empleado = None

        # Si la caja se abre, asignar automáticamente un empleado libre si no tiene uno
        if estado in ("abierta", "activa"):
            emp_actual = id_empleado
            if emp_actual is _UNSET or emp_actual is None:
                self.cursor.execute("SELECT id_empleado FROM cajas WHERE id = ?", (id,))
                caja_actual = self.cursor.fetchone()
                if caja_actual and caja_actual[0] is not None:
                    emp_actual = caja_actual[0]

            if emp_actual is _UNSET or emp_actual is None:
                # Buscar empleados activos
                self.cursor.execute("SELECT id FROM empleados WHERE activo = 1")
                todos_empleados = [r[0] for r in self.cursor.fetchall()]
                
                # Buscar empleados ya asignados a otras cajas abiertas
                self.cursor.execute("SELECT id_empleado FROM cajas WHERE estado IN ('abierta', 'activa') AND id != ? AND id_empleado IS NOT NULL", (id,))
                empleados_ocupados = [r[0] for r in self.cursor.fetchall()]
                
                empleados_libres = [e for e in todos_empleados if e not in empleados_ocupados]
                if empleados_libres:
                    id_empleado = empleados_libres[0]

        campos: List[str] = []
        parametros: List[Any] = []

        if estado is not None:
            # Normalizar "activa" a "abierta"
            if estado == "activa":
                estado = "abierta"
            campos.append("estado = ?")
            parametros.append(estado)
        if id_empleado is not _UNSET:
            campos.append("id_empleado = ?")
            parametros.append(id_empleado)

        if not campos:
            return False

        campos.append("actualizado_en = ?")
        parametros.append(self._now_iso())
        parametros.append(id)

        self.cursor.execute(
            f"UPDATE cajas SET {', '.join(campos)} WHERE id = ?",
            parametros,
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    # Método para obtener los datos de una caja específica por su ID, incluyendo estado y empleado asignado.
    def obtener_caja(self, id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una caja por su identificador.

        Args:
            id: Identificador único de la caja.

        Returns:
            Dict con la caja o None si no existe.
        """
        self.cursor.execute(
            "SELECT id, estado, id_empleado, actualizado_en FROM cajas WHERE id = ?",
            (id,),
        )
        row = self.cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row, ["id", "estado", "id_empleado", "actualizado_en"])

    # Método para obtener una lista de todas las cajas registradas en la base de datos, con sus estados y empleados asignados.
    def obtener_cajas(self) -> List[Dict[str, Any]]:
        """Obtiene todas las cajas registradas.

        Returns:
            Lista de dicts con estructura: {"id": str, "estado": str, "id_empleado": int/None, "actualizado_en": str}.
        """
        self.cursor.execute(
            "SELECT id, estado, id_empleado, actualizado_en FROM cajas ORDER BY id"
        )
        rows = self.cursor.fetchall()
        return [self._row_to_dict(row, ["id", "estado", "id_empleado", "actualizado_en"]) for row in rows]

    # ------------------------------------------------------------------
    # Registro y consulta de métricas
    # ------------------------------------------------------------------

    # Método para registrar una nueva medición de tiempo medio de espera, asociada opcionalmente a una caja concreta y con fuente de cálculo.
    def registrar_metrica(
        self,
        tiempo_medio_espera_segundos: float,
        id_caja: Optional[str] = None,
        fuente: str = "decision_processor",
        registrada_en: Optional[str] = None,
    ) -> int:
        """Registra una medición de tiempo medio de espera.

        Args:
            tiempo_medio_espera_segundos: Tiempo medio de espera registrado en segundos.
            id_caja: Caja concreta a la que aplica la medición. Si es None, se guarda como valor global.
            fuente: Origen del cálculo (por ejemplo, "decision_processor").
            registrada_en: Timestamp ISO 8601 opcional. Si no se pasa, se usa la fecha actual.

        Returns:
            ID del registro insertado.

        Example:
            with DatabaseMSQ() as db:
                db.registrar_metrica(
                    tiempo_medio_espera_segundos=45.3,
                    id_caja="Caja_1",
                    fuente="decision_processor"
                )
        """
        self.cursor.execute(
            """
            INSERT INTO metricas (
                registrada_en,
                id_caja,
                tiempo_medio_espera_segundos,
                fuente
            ) VALUES (?, ?, ?, ?)
            """,
            (
                registrada_en or self._now_iso(),
                id_caja,
                float(tiempo_medio_espera_segundos),
                fuente,
            ),
        )
        self.conn.commit()
        return int(self.cursor.lastrowid)

    # Método para obtener mediciones de tiempo medio de espera, con filtros opcionales por caja, rango de fechas y fuente.
    def obtener_metricas(
        self,
        id_caja: Optional[str] = None,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        limite: int = 1000,
        solo_global: bool = False,
    ) -> List[Dict[str, Any]]:
        """Obtiene mediciones de tiempo medio de espera con filtros opcionales.

        Args:
            id_caja: Filtro opcional por caja concreta.
            desde: Fecha/hora ISO 8601 mínima inclusiva.
            hasta: Fecha/hora ISO 8601 máxima inclusiva.
            limite: Máximo número de registros a retornar (default 1000).
            solo_global: Si True, retorna solo mediciones globales (id_caja NULL).

        Returns:
            Lista de dicts con estructura: {"id": int, "registrada_en": str, "id_caja": str|None, "tiempo_medio_espera_segundos": float, "fuente": str}.

        Example:
            with DatabaseMSQ() as db:
                ultimas = db.obtener_metricas(id_caja="Caja_1", limite=50)
                historico_global = db.obtener_metricas(solo_global=True, desde="2026-05-01T00:00:00Z")
        """
        query = [
            "SELECT id, registrada_en, id_caja, tiempo_medio_espera_segundos, fuente",
            "FROM metricas",
        ]
        filtros: List[str] = []
        parametros: List[Any] = []

        if solo_global:
            filtros.append("id_caja IS NULL")
        elif id_caja is not None:
            filtros.append("id_caja = ?")
            parametros.append(id_caja)

        if desde is not None:
            filtros.append("registrada_en >= ?")
            parametros.append(desde)

        if hasta is not None:
            filtros.append("registrada_en <= ?")
            parametros.append(hasta)

        if filtros:
            query.append("WHERE " + " AND ".join(filtros))

        query.append("ORDER BY id DESC LIMIT ?")
        parametros.append(limite)

        self.cursor.execute(" ".join(query), parametros)
        rows = self.cursor.fetchall()
        columnas = ["id", "registrada_en", "id_caja", "tiempo_medio_espera_segundos", "fuente"]

        result: List[Dict[str, Any]] = []
        for row in rows:
            item = self._row_to_dict(row, columnas)
            result.append(item)
        return result

    # ------------------------------------------------------------------
    # Operaciones sobre empleados
    # ------------------------------------------------------------------

    # Método para crear un nuevo empleado en la base de datos, con nombre, apellidos y pulsera IoT opcionalmente asociada.
    def crear_empleado(self, nombre: str, apellidos: str, id_pulsera: Optional[str] = None) -> int:
        """Crea un nuevo registro de empleado.

        Args:
            nombre: Nombre del empleado.
            apellidos: Apellidos del empleado.
            id_pulsera: ID único de la pulsera IoT asociada (opcional, debe ser único).

        Returns:
            ID del empleado creado.

        Raises:
            sqlite3.IntegrityError: Si id_pulsera ya existe en otro empleado.

        Example:
            with DatabaseMSQ() as db:
                emp_id = db.crear_empleado("Juan", "García", "001")
                print(f"Empleado creado con ID: {emp_id}")
        """
        self.cursor.execute(
            """
            INSERT INTO empleados (nombre, apellidos, id_pulsera, activo, creado_en, actualizado_en)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (nombre, apellidos, id_pulsera, self._now_iso(), self._now_iso()),
        )
        self.conn.commit()
        return int(self.cursor.lastrowid)

    # Método para listar todos los empleados registrados, con opción de filtrar solo los activos.
    def listar_empleados(self, activos: bool = False) -> List[Dict[str, Any]]:
        """Lista todos los empleados registrados.

        Args:
            activos: Si True, retorna solo empleados activos. Si False, retorna todos.

        Returns:
            Lista de diccionarios con datos de empleados (id, nombre, apellidos, etc.).

        Example:
            with DatabaseMSQ() as db:
                todos = db.listar_empleados(activos=False)
                activos = db.listar_empleados(activos=True)
                for emp in activos:
                    print(f"{emp['nombre']} {emp['apellidos']}")
        """
        query = "SELECT id, nombre, apellidos, id_pulsera, activo, creado_en, actualizado_en FROM empleados"
        parametros: List[Any] = []
        if activos:
            query += " WHERE activo = ?"
            parametros.append(1)
        query += " ORDER BY apellidos, nombre, id"

        self.cursor.execute(query, parametros)
        rows = self.cursor.fetchall()
        columnas = ["id", "nombre", "apellidos", "id_pulsera", "activo", "creado_en", "actualizado_en"]
        
        result = []
        for row in rows:
            item = self._row_to_dict(row, columnas)
            item["activo"] = bool(item["activo"])
            result.append(item)
        return result

    # Método para obtener los datos de un empleado específico por su ID, incluyendo nombre, apellidos, pulsera asociada y estado activo.
    def obtener_empleado(self, id_empleado: int) -> Optional[Dict[str, Any]]:
        """Obtiene los datos de un empleado por su ID.

        Args:
            id_empleado: ID del empleado.

        Returns:
            Dict con los datos del empleado, o None si no existe.

        Example:
            with DatabaseMSQ() as db:
                emp = db.obtener_empleado(1)
                if emp:
                    print(f"Empleado: {emp['nombre']} {emp['apellidos']}")
                    print(f"Pulsera: {emp['id_pulsera']}")
                    print(f"Activo: {bool(emp['activo'])}")
        """
        self.cursor.execute(
            "SELECT id, nombre, apellidos, id_pulsera, activo, creado_en, actualizado_en FROM empleados WHERE id = ?",
            (id_empleado,),
        )
        row = self.cursor.fetchone()
        if row is None:
            return None
        
        item = self._row_to_dict(row, ["id", "nombre", "apellidos", "id_pulsera", "activo", "creado_en", "actualizado_en"])
        item["activo"] = bool(item["activo"])
        return item

    # Método para actualizar los datos de un empleado existente, con opciones para modificar nombre, apellidos, pulsera asociada y estado activo.
    def actualizar_empleado(
        self,
        id_empleado: int,
        nombre: Optional[str] = None,
        apellidos: Optional[str] = None,
        id_pulsera: Optional[str] = None,
        activo: Optional[bool] = None,
    ) -> bool:
        """Actualiza los datos de un empleado existente.

        Solo actualiza los campos proporcionados (los None se ignoran).
        Actualiza automáticamente el timestamp 'actualizado_en'.

        Args:
            id_empleado: ID del empleado a actualizar.
            nombre: Nuevo nombre (opcional).
            apellidos: Nuevos apellidos (opcional).
            id_pulsera: Nuevo ID de pulsera (opcional).
            activo: Nuevo estado (True=activo, False=inactivo, opcional).

        Returns:
            True si la actualización fue exitosa, False si no hay cambios o el empleado no existe.

        Example:
            with DatabaseMSQ() as db:
                actualizado = db.actualizar_empleado(
                    1,
                    nombre="Juan",
                    id_pulsera="pulsera-002"
                )
                if actualizado:
                    print("Empleado actualizado")
        """
        campos: List[str] = []
        parametros: List[Any] = []

        if nombre is not None:
            campos.append("nombre = ?")
            parametros.append(nombre)
        if apellidos is not None:
            campos.append("apellidos = ?")
            parametros.append(apellidos)
        if id_pulsera is not None:
            campos.append("id_pulsera = ?")
            parametros.append(id_pulsera)
        if activo is not None:
            campos.append("activo = ?")
            parametros.append(1 if activo else 0)

        if not campos:
            return False

        campos.append("actualizado_en = ?")
        parametros.append(self._now_iso())
        parametros.append(id_empleado)

        self.cursor.execute(
            f"UPDATE empleados SET {', '.join(campos)} WHERE id = ?",
            parametros,
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    # Método para eliminar un empleado de la base de datos, identificándolo por su ID. Retorna True si se eliminó, False si no existía.
    def eliminar_empleado(self, id_empleado: int) -> bool:
        """Elimina un empleado de la base de datos.

        Args:
            id_empleado: ID del empleado a eliminar.

        Returns:
            True si se eliminó, False si el empleado no existía.

        Example:
            with DatabaseMSQ() as db:
                eliminado = db.eliminar_empleado(1)
                if eliminado:
                    print("Empleado eliminado")
        """
        self.cursor.execute("DELETE FROM empleados WHERE id = ?", (id_empleado,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    


    # ------------------------------------------------------------------
    # Turnos y estado de cajas
    # ------------------------------------------------------------------

    # Método para actualizar la organización de turnos y precedencia de empleados para uno o varios días/turnos a la vez, con inserción o actualización según corresponda.
    def actualizar_turnos(self, turnos_update: List[Dict[str, Any]]) -> None:
        """Modifica uno o varios turnos a la vez.

        Args:
            turnos_update: Lista de diccionarios indicando el día, turno y la nueva lista de empleados.
                           Obligatorio: 'dia_semana', 'turno'. Opcional: 'orden' (lista vacía por defecto).
        
        Example:
            with DatabaseMSQ() as db:
                db.actualizar_turnos([
                    {"dia_semana": "lunes", "turno": "mañana", "orden": [{"id": 1}, {"id": 2}]},
                    {"dia_semana": "martes", "turno": "tarde", "orden": []}
                ])
        """
        now = self._now_iso()
        records = [
            (
                t["dia_semana"],
                t["turno"],
                self._json_dumps(t.get("orden", [])) or "[]",
                now
            )
            for t in turnos_update
        ]

        self.cursor.executemany(
            """
            INSERT INTO turnos (dia_semana, turno, orden_json, actualizado_en)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(dia_semana, turno) DO UPDATE SET
                orden_json = excluded.orden_json,
                actualizado_en = excluded.actualizado_en
            """,
            records
        )
        self.conn.commit()

    # Método para obtener toda la semana de turnos o un subconjunto específico, listo para iterar, con filtros opcionales por día de la semana y turno.
    def obtener_turnos(self, dia_semana: Optional[str] = None, turno: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene toda la semana de turnos o un subconjunto específico, listo para iterar.

        Args:
            dia_semana: Filtro opcional por día de la semana.
            turno: Filtro opcional por turno (e.g., "mañana", "tarde").

        Returns:
            Lista de turnos. Si no se especifican filtros, devuelve todos los registros (la semana completa).
            
        Example:
            with DatabaseMSQ() as db:
                # Toda la semana
                semana = db.obtener_turnos()
                # Solo los lunes por la mañana
                lunes_manana = db.obtener_turnos("lunes", "mañana")
        """
        query = "SELECT id, dia_semana, turno, orden_json, actualizado_en FROM turnos"
        filtros: List[str] = []
        parametros: List[Any] = []

        if dia_semana is not None:
            filtros.append("dia_semana = ?")
            parametros.append(dia_semana)
        if turno is not None:
            filtros.append("turno = ?")
            parametros.append(turno)

        if filtros:
            query += " WHERE " + " AND ".join(filtros)
        query += " ORDER BY dia_semana, turno"

        self.cursor.execute(query, parametros)
        rows = self.cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            item = self._row_to_dict(row, ["id", "dia_semana", "turno", "orden_json", "actualizado_en"])
            item["orden"] = self._json_loads(item.pop("orden_json")) or []
            result.append(item)
        return result

    # ------------------------------------------------------------------
    # Utilidades y cierre de conexión
    # ------------------------------------------------------------------

    # Método para cerrar la conexión a la base de datos, liberando recursos. No es necesario si se usa context manager (with).
    def close(self) -> None:
        """Cierra la conexión a la base de datos.

        Generalmente no es necesario si se usa context manager (with).

        Example:
            db = DatabaseMSQ()
            try:
                db.registrar_instantanea({"Caja_1": ["sinCarro", "sinCarro", "sinCarro"]})
            finally:
                db.close()
        """
        self.conn.close()

    # Soporte para context manager: with DatabaseMSQ() as db:
    def __enter__(self):
        """Soporte para context manager: with DatabaseMSQ() as db:"""
        return self

    # Soporte para context manager: cierra la conexión automáticamente al salir del bloque with.
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la conexión automáticamente al salir del contexto."""
        self.close()
