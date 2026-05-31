# Importaciones y utilidades de sistema
import os
import sys
import subprocess
import time
import webbrowser
import shutil
from pathlib import Path

# ------------------------------------------------------------------
# Preparación del Entorno y Verificación de Dependencias
# ------------------------------------------------------------------

# Verifica e instala automáticamente las dependencias del proyecto (Python y Node.js), asegurando que el entorno esté listo.
def setup_dependencies() -> None:
    """Verifica y prepara el entorno de ejecución del proyecto.

    Realiza las siguientes tareas de configuración antes del inicio:
    1. Asegura la instalación silenciosa de los paquetes de Python definidos en backend/requirements.txt.
    2. Comprueba y ejecuta 'npm install' en el directorio 'simulacion' si node_modules no existe.
    3. Comprueba y ejecuta 'npm install' en el directorio 'frontend' si node_modules no existe.
    4. Copia automáticamente frontend/example.env a frontend/.env si este último no está presente.
    5. Copia automáticamente simulacion/example.env a simulacion/.env si este último no está presente.
    """
    print("[Orchestrator] --- Verificando y preparando el entorno ---")
    
    # 1. Asegurar dependencias de Python en backend
    requirements_path = Path("backend/requirements.txt")
    if requirements_path.exists():
        print("[Orchestrator] Asegurando dependencias de Python (backend/requirements.txt). Esto puede tardar varios minutos ...")
        try:
            # Ejecuta pip install de forma silenciosa redirigiendo la salida estándar y de errores para no saturar la consola
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[Orchestrator] Dependencias de Python verificadas.")
        except Exception as e:
            print(f"[WARNING] Error verificando dependencias de Python: {e}")
            print("[Orchestrator] Continuando ejecución...")
    
    # 2. Asegurar dependencias de Node.js en simulacion
    sim_node_modules = Path("simulacion/node_modules")
    if not sim_node_modules.exists():
        print("[Orchestrator] 'simulacion/node_modules' no encontrado. Ejecutando 'npm install'...")
        try:
            # Instala los paquetes de npm en el subdirectorio de la simulación
            subprocess.check_call("npm install", cwd="simulacion", shell=True)
            print("[Orchestrator] Dependencias de 'simulacion' instaladas.")
        except Exception as e:
            print(f"[ERROR] Error al instalar dependencias de simulacion: {e}")
    else:
        print("[Orchestrator] Dependencias de 'simulacion' detectadas.")

    # 3. Asegurar dependencias de Node.js en frontend
    front_node_modules = Path("frontend/node_modules")
    if not front_node_modules.exists():
        print("[Orchestrator] 'frontend/node_modules' no encontrado. Ejecutando 'npm install'...")
        try:
            # Instala los paquetes de npm en el subdirectorio del panel de control
            subprocess.check_call("npm install", cwd="frontend", shell=True)
            print("[Orchestrator] Dependencias de 'frontend' instaladas.")
        except Exception as e:
            print(f"[ERROR] Error al instalar dependencias de frontend: {e}")
    else:
        print("[Orchestrator] Dependencias de 'frontend' detectadas.")

    # 4. Asegurar archivo .env de configuración en frontend
    front_env = Path("frontend/.env")
    front_example = Path("frontend/example.env")
    if not front_env.exists() and front_example.exists():
        print("[Orchestrator] 'frontend/.env' no encontrado. Copiando desde 'frontend/example.env'...")
        try:
            # Realiza un fallback copiando el archivo de ejemplo para asegurar las variables de entorno de Vite en la primera ejecución
            shutil.copy(str(front_example), str(front_env))
            print("[Orchestrator] Archivo 'frontend/.env' creado con éxito.")
        except Exception as e:
            print(f"[ERROR] Error al copiar 'frontend/example.env': {e}")
        
    # 5. Asegurar archivo .env de configuración en simulacion
    sim_env = Path("simulacion/.env")
    sim_example = Path("simulacion/example.env")
    if not sim_env.exists() and sim_example.exists():
        print("[Orchestrator] 'simulacion/.env' no encontrado. Copiando desde 'simulacion/example.env'...")
        try:
            # Realiza un fallback copiando el archivo de ejemplo para asegurar las variables de entorno de la simulación
            shutil.copy(str(sim_example), str(sim_env))
            print("[Orchestrator] Archivo 'simulacion/.env' creado con éxito.")
        except Exception as e:
            print(f"[ERROR] Error al copiar 'simulacion/example.env': {e}")
        
    print("[Orchestrator] --- Entorno listo ---\n")


# ------------------------------------------------------------------
# Lanzamiento de Servicios y Orquestación Principal
# ------------------------------------------------------------------

# Orquesta e inicia de forma ordenada todos los servicios del ecosistema Mercadona SmartQ en terminales independientes de Windows.
def main() -> None:
    """Arranca de manera secuencial los cinco servicios principales del sistema.

    El flujo de arranque realiza lo siguiente:
    1. Prepara las dependencias de todos los proyectos (setup_dependencies).
    2. Levanta la API del backend en una ventana independiente.
    3. Espera 3 segundos a que los puertos de red estén listos.
    4. Levanta el simulador de cajas 3D y el dashboard del frontend en sendas terminales.
    5. Espera 4 segundos para que se completen las compilaciones rápidas de Vite.
    6. Abre el navegador web por defecto apuntando a ambos servicios.
    7. Espera 1 segundo.
    8. Lanza el motor de visión y el procesador de decisiones en terminales dedicadas.
    """
    # Ejecutar la comprobación y la preparación del entorno antes de arrancar los servicios
    setup_dependencies()

    print("[Orchestrator] Arrancando todos los servicios de Mercadona SmartQ en terminales independientes...")

    # 1. Levantar Servidor de API (FastAPI) en una nueva ventana de terminal
    print("[Orchestrator] Lanzando Servidor API en Terminal 1...")
    # Abre una consola de CMD nativa de Windows que permanece abierta (/k) mostrando el flujo de la API
    subprocess.Popen('start cmd /k "cd backend && python -m api.main"', shell=True)

    # Esperar 3 segundos para que FastAPI se levante de forma completa y prepare los puertos de red
    print("[Orchestrator] Esperando a que el Servidor API responda...")
    time.sleep(3.0)

    # 2. Levantar la Simulación 3D (Vite/Vue) en otra ventana de terminal
    print("[Orchestrator] Lanzando Simulación 3D en Terminal 2...")
    subprocess.Popen('start cmd /k "cd simulacion && npm run dev"', shell=True)

    # 3. Levantar el Frontend Dashboard (Vite/Vue) en otra ventana de terminal
    print("[Orchestrator] Lanzando Frontend Dashboard en Terminal 3...")
    subprocess.Popen('start cmd /k "cd frontend && npm run dev"', shell=True)

    # Esperar 4 segundos para dar un margen de compilación inicial de desarrollo a los servidores de Vite
    time.sleep(4.0)

    # Definición de las URLs locales de los servicios web cargados
    dashboard_url = "http://localhost:5173"
    simulation_url = "http://localhost:5174"
    
    # Abre el panel de control y la simulación 3D interactiva en pestañas del navegador web predeterminado
    print(f"[Orchestrator] Abriendo Frontend Dashboard en el navegador: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(0.5)
    print(f"[Orchestrator] Abriendo Simulación 3D en el navegador: {simulation_url}")
    webbrowser.open(simulation_url)
    
    time.sleep(1.0)

    # 4. Levantar el Motor de Visión Artificial (OpenCV/YOLO) en otra ventana de terminal
    print("[Orchestrator] Lanzando Motor de Visión (OpenCV + YOLOv8) en Terminal 4...")
    subprocess.Popen('start cmd /k "cd backend && python main.py"', shell=True)

    # 5. Levantar el Motor de Decisiones (Decision Processor) en otra ventana de terminal
    print("[Orchestrator] Lanzando Motor de Decisiones (Decision Processor) en Terminal 5...")
    subprocess.Popen('start cmd /k "cd backend && python decision_processor.py"', shell=True)

    print("[Orchestrator] Todos los servicios han sido lanzados en terminales individuales.")


# Bloque de ejecución principal del script
if __name__ == "__main__":
    main()

