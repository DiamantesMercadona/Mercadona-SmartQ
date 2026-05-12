from paho.mqtt import client as mqtt

def on_message(client, userdata, msg):
    print("📺 Display:", msg.payload.decode())

client = mqtt.Client()
client.connect("localhost", 1883, 60)
client.subscribe("tienda/display/caja/mensaje")
client.on_message = on_message
client.loop_forever()
