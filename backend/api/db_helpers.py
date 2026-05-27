from typing import Any, Dict, List
import sys
from pathlib import Path

# Agregar el directorio backend al path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import DatabaseMSQ


def init_db() -> None:
    """Inicializa la base de datos."""
    with DatabaseMSQ():
        pass


def _latest_queue_lengths(db: DatabaseMSQ) -> Dict[str, int]:
    """Obtiene las longitudes de las colas desde la última instantánea."""
    snapshots = db.obtener_instantaneas(limite=1)
    if not snapshots:
        return {}

    estado_cajas = snapshots[0].get("estado_cajas") or {}
    return {
        str(queue_id): len(groups) if isinstance(groups, list) else 0
        for queue_id, groups in estado_cajas.items()
    }


def _queue_from_caja(caja: Dict[str, Any], lengths: Dict[str, int]) -> Dict[str, Any]:
    """Convierte una caja a formato de cola."""
    queue_id = str(caja["id"])
    return {
        "id": queue_id,
        "name": f"Caja {queue_id}",
        "length": lengths.get(queue_id, 0),
        "status": caja["estado"],
        "id_empleado": caja.get("id_empleado"),
        "actualizado_en": caja.get("actualizado_en"),
    }


def get_queues() -> List[Dict[str, Any]]:
    """Obtiene todas las colas."""
    with DatabaseMSQ() as db:
        lengths = _latest_queue_lengths(db)
        return [_queue_from_caja(caja, lengths) for caja in db.obtener_cajas()]


def update_queue(queue_id: int | str, length: int, status: str) -> bool:
    """Actualiza el estado de una cola."""
    del length
    with DatabaseMSQ() as db:
        return db.actualizar_caja(id=str(queue_id), estado=status)
