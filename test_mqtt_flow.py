#!/usr/bin/env python3
"""
Simple MQTT test to verify if messages are being sent/received correctly
"""

import sys
import time
import paho.mqtt.client as mqtt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

def test_mqtt_flow():
    print("=== MQTT Message Flow Test ===")
    
    app = QApplication(sys.argv)
    
    # Read settings
    settings = QSettings('sets/settings.ini', QSettings.Format.IniFormat)
    server_address = settings.value('server_address', '')
    server_password = settings.value('server_password', '')
    mqtt_address = settings.value('mqtt_address', '')
    
    topic_prefix = f"{server_address}/{server_password}"
    
    print(f"Using topic prefix: '{topic_prefix}'")
    print(f"MQTT broker: {mqtt_address}")
    
    messages_received = []
    
    def on_connect(client, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code {rc}")
        # Subscribe to all topics under our prefix
        client.subscribe(f"{topic_prefix}/#")
        print(f"Subscribed to: {topic_prefix}/#")
        
        # Send a test registration message
        test_topic = f"{topic_prefix}/server/status"
        test_message = "register|test-client-id|TEST-HOSTNAME"
        print(f"\\nSending test message:")
        print(f"  Topic: {test_topic}")
        print(f"  Message: {test_message}")
        client.publish(test_topic, test_message)
    
    def on_message(client, userdata, message):
        topic = message.topic
        payload = message.payload.decode('utf-8', errors='ignore')
        print(f"\\nReceived message:")
        print(f"  Topic: {topic}")
        print(f"  Payload: {payload}")
        messages_received.append((topic, payload))
    
    # Create MQTT client
    client = mqtt.Client(client_id="test-mqtt-flow")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print(f"\\nConnecting to {mqtt_address}...")
        client.connect(mqtt_address, 1883, 60)
        client.loop_start()
        
        # Wait for messages
        print("\\nWaiting for messages (10 seconds)...")
        time.sleep(10)
        
        client.loop_stop()
        client.disconnect()
        
        print(f"\\n=== Test Results ===")
        print(f"Messages received: {len(messages_received)}")
        for i, (topic, payload) in enumerate(messages_received):
            print(f"  {i+1}. {topic}: {payload}")
            
        if not messages_received:
            print("WARNING: No messages received. Check if server is running.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mqtt_flow()