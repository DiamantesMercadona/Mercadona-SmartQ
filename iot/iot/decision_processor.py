import json
import redis
import requests

r = redis.Redis(host="localhost", port=6379, db=0)

UMBRAL_COLA = 6

def procesar_evento(data):
    personas_en_cola = data.get("cola", 0)

    if personas_en_cola > UMBRAL_COLA:
        print("⚠️ Demasiada cola, abrir nueva caja")

        # Vibrar pulsera del encargado
        requests.post("http://localhost:8000/iot/vibrar/01")

        # Mostrar mensaje en display
        requests.post("http://localhost:8000/iot/display", json="Abrir nueva caja")

def escuchar():
    pubsub = r.pubsub()
    pubsub.subscribe("vision_events")

    print("Decision Processor escuchando...")

    for mensaje in pubsub.listen():
        if mensaje["type"] == "message":
            data = json.loads(mensaje["data"])
            procesar_evento(data)

if __name__ == "__main__":
    escuchar()
