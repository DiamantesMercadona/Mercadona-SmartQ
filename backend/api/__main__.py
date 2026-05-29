"""
Entry point para ejecutar la API como módulo.
"""
import sys
from pathlib import Path

# Agregar directorios al path
BACKEND_DIR = Path(__file__).resolve().parent.parent
API_DIR = Path(__file__).resolve().parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

# Ahora importar la app
import uvicorn
from .main import app

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
