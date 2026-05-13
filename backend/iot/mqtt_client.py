from paho.mqtt import client as mqtt

mqtt_client = mqtt.Client()
mqtt_client.connect("localhost", 1883, 60)
