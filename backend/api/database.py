from pathlib import Path
import sys
from typing import Any, Dict, List

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import DatabaseMSQ


def init_db() -> None:
    with DatabaseMSQ():
        pass


def _latest_queue_lengths(db: DatabaseMSQ) -> Dict[str, int]:
    snapshots = db.obtener_instantaneas(limite=1)
    if not snapshots:
        return {}

    estado_cajas = snapshots[0].get("estado_cajas") or {}
    return {
        str(queue_id): len(groups) if isinstance(groups, list) else 0
        for queue_id, groups in estado_cajas.items()
    }


def _queue_from_caja(caja: Dict[str, Any], lengths: Dict[str, int]) -> Dict[str, Any]:
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
    with DatabaseMSQ() as db:
        lengths = _latest_queue_lengths(db)
        return [_queue_from_caja(caja, lengths) for caja in db.obtener_cajas()]


def update_queue(queue_id: int | str, length: int, status: str) -> bool:
    del length
    with DatabaseMSQ() as db:
        return db.actualizar_caja(id=str(queue_id), estado=status)
