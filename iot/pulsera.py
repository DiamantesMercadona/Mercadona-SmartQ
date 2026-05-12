from paho.mqtt import client as mqtt

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    if payload == "1":
        print("💥 Pulsera vibrando")
    else:
        print("Pulsera detenida")

client = mqtt.Client()
client.connect("localhost", 1883, 60)
client.subscribe("tienda/pulsera/01/vibrar")
client.on_message = on_message
client.loop_forever()
