from paho.mqtt import client as mqtt
import requests

BACKEND_URL = "http://localhost:8000/display/evento"

def on_message(client, userdata, msg):
    mensaje = msg.payload.decode()
    print("📺 Display:", mensaje)

    # Enviar evento al backend
    try:
        requests.post(BACKEND_URL, json={
            "mensaje": mensaje
        })
        print("📡 Evento de display enviado al backend")
    except Exception as e:
        print("❌ Error enviando evento al backend:", e)


client = mqtt.Client()
client.connect("localhost", 1883, 60)
client.subscribe("tienda/display/caja/mensaje")
client.on_message = on_message
client.loop_forever()
