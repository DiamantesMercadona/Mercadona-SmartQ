from paho.mqtt import client as mqtt
import requests

BACKEND_URL = "http://localhost:8000/pulsera/evento"

def on_message(client, userdata, msg):
    payload = msg.payload.decode()

    if payload == "1":
        print("💥 Pulsera vibrando")
        evento = "vibracion"
    else:
        print("Pulsera detenida")
        evento = "detenida"

    # Enviar evento al backend
    try:
        requests.post(BACKEND_URL, json={
            "pulsera_id": "01",
            "evento": evento
        })
        print("📡 Evento enviado al backend")
    except Exception as e:
        print("❌ Error enviando evento al backend:", e)


client = mqtt.Client()
client.connect("localhost", 1883, 60)
client.subscribe("tienda/pulsera/01/vibrar")
client.on_message = on_message
client.loop_forever()
