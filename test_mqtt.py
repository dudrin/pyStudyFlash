#!/usr/bin/env python3
"""
Minimal MQTT connection test to isolate the disconnection issue
"""

import paho.mqtt.client as mqtt
import time
import uuid

def on_connect(client, userdata, flags, rc, properties=None):
    print(f'Connected flags {flags}, result code={rc}')
    if rc == 0:
        print('Successfully connected to MQTT broker')
        # Subscribe to test topics
        client.subscribe('dudkate@yandex.ru/123456/client/status')
        print('Subscribed to test topic')
        
        # Publish test message
        client.publish('dudkate@yandex.ru/123456/server/status', 'test message')
        print('Published test message')
    else:
        print(f'Connection failed with code {rc}')

def on_disconnect(client, userdata, rc, properties=None):
    print(f'Disconnected with code {rc}')

def on_message(client, userdata, message):
    print(f'Received message on topic {message.topic}: {message.payload.decode()}')

def main():
    print('Testing MQTT connection...')
    
    client_id = str(uuid.uuid4()) + str(time.time())
    print(f'Client ID: {client_id}')
    
    # Setup MQTT client
    client_kwargs = {"client_id": client_id, "clean_session": False}
    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api is not None:
        version_attr = getattr(callback_api, "VERSION1", None) or getattr(callback_api, "V1", None)
        if version_attr is not None:
            client_kwargs["callback_api_version"] = version_attr
    
    client = mqtt.Client(**client_kwargs)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    try:
        print('Connecting to broker.hivemq.com:1883...')
        client.connect('broker.hivemq.com', 1883, 60)
        client.loop_start()
        
        # Keep running for 10 seconds
        print('Waiting 10 seconds...')
        time.sleep(10)
        
        print('Disconnecting...')
        client.disconnect()
        client.loop_stop()
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()