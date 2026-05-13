import json
import redis
import requests

# Conexión a Redis
r = redis.Redis(host="localhost", port=6379, db=0)

# Umbral para tomar decisiones
UMBRAL_COLA = 6

def procesar_evento(data):
    """
    Procesa un evento de vídeo recibido desde Redis.
    Espera un JSON con: { "people_count": X }
    """
    personas_en_cola = data.get("people_count", 0)

    if personas_en_cola > UMBRAL_COLA:
        print("⚠️ Demasiada cola, abrir nueva caja")

        # Vibrar pulsera del encargado
        requests.post("http://localhost:8000/api/v1/vibrar/01")

        # Mostrar mensaje en display
        requests.post(
            "http://localhost:8000/api/v1/display",
            json="Abrir nueva caja"
        )

def escuchar():
    """
    Escucha el canal Redis donde se publican los eventos de vídeo.
    """
    pubsub = r.pubsub()
    pubsub.subscribe("video_events")  # Canal correcto

    print("Decision Processor escuchando eventos de vídeo...")

    for mensaje in pubsub.listen():
        if mensaje["type"] == "message":
            try:
                data = json.loads(mensaje["data"])
                procesar_evento(data)
            except Exception as e:
                print("❌ Error procesando evento:", e)

if __name__ == "__main__":
    escuchar()
