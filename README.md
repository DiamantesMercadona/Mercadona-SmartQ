# Mercadona SmartQ (MSQ)

Mercadona Smart Queue (MSQ) es un sistema de visión por computador para la monitorización inteligente de colas en líneas de cajas, que permite la detección automática de saturación y la activación inmediata de protocolos de apertura y cierre de cajas para la gestión del flujo de clientes en tiempo real.

---

## 🛠️ Requisitos previos

Antes de comenzar, asegúrate de tener instalados los siguientes entornos en tu máquina:

1. **Python (Versión 3.8 o superior)**:
   * Requerido para todo el backend
   * Descárgalo desde [python.org](https://www.python.org/downloads/).
   * **IMPORTANTE (Windows):** Durante la instalación, asegúrate de marcar la casilla *"Add Python to PATH"* para habilitar los comandos globales.
2. **Node.js (Versión 16.0 o superior)**:
   * Requerido para la simulación y el frontend.
   * Descárgalo e instálalo desde [nodejs.org](https://nodejs.org/).

---

## 🚀 Instalación y ejecución

El sistema consta de cinco servicios independientes:
- API (FastAPI)
- Simulación 3D (Vite/Vue)
- Frontend Dashboard (Vite/Vue)
- Motor de Visión (OpenCV + YOLOv8)
- Motor de Decisiones (Decision Processor)

### ⚡ Método recomendado: Ejecución automática

Un script orquestador inteligente en la raíz del proyecto se encarga de preparar todo el entorno y lanzar los servicios, detectando dependencias faltantes e instalándolas automáticamente, verificando que todos los puertos estén libres y levantando los servicios en terminales independientes en el orden correcto con los retardos correspondientes.


#### Instrucciones:
1. Abre una terminal en la raíz del proyecto.
2. Ejecuta el siguiente comando:
   ```bash
   python run_all.py
   ```
3. Espera a que todos los servicios se inicien y las páginas se abran en tu navegador.

---

## 💻 Método alternativo: Ejecución manual

Si prefieres instalar y ejecutar cada servicio de forma individual de manera tradicional, sigue estas instrucciones:

### 📋 Fase 1: Instalación de dependencias manual

Abre una terminal en la raíz del proyecto y prepara los entornos:

#### 1. Servidor backend (Python)
```bash
cd backend
python -m pip install -r requirements.txt
```

#### 2. Simulación 3D (Node.js/Vue)
```bash
cd ../simulacion
npm install
```

#### 3. Frontend dashboard (Node.js/Vue)
```bash
cd ../frontend
npm install
```

---

### ⚙️ Fase 2: Ejecución de los servicios (Terminales independientes)

Abre terminales separadas en la raíz del proyecto y sigue este orden:

#### 🖥️ Terminal 1: Servidor de la API (FastAPI)
Expone los endpoints de datos e inicia el broker para WebSockets.
```bash
cd backend
python -m api.main
```

#### 🎮 Terminal 2: Simulación 3D (Vite/Vue)
Inicia la simulación 3D interactiva en `http://localhost:5174`.
```bash
cd simulacion
npm run dev
```

#### 📊 Terminal 3: Frontend dashboard (Vite/Vue)
Inicia el panel de control del gerente/cajero en `http://localhost:5173`.
```bash
cd frontend
npm run dev
```

#### 👁️ Terminal 4: Motor de visión artificial (OpenCV + YOLOv8)
Arranca el rastreador de clientes conectándose a la simulación.
```bash
cd backend
python main.py
```

#### 🧠 Terminal 5: Motor de decisiones (Decision Processor)
Procesa continuamente las métricas y los tiempos estimados de espera (SLA) para generar sugerencias automáticas de apertura/cierre de cajas.
```bash
cd backend
python decision_processor.py
```

---

## 🧪 Pruebas unitarias

El proyecto cuenta con una batería de pruebas unitarias para validar de forma automatizada el funcionamiento de la base de datos, el motor de visión y los endpoints de la API.

Puedes ejecutar todas las pruebas desde la raíz del proyecto con la siguiente instrucción:

```bash
python -m unittest discover -s backend/tests
```




