#!/usr/bin/env python3
"""
Direct MQTT test to verify client role assignment
"""

import sys
import time
import uuid
import paho.mqtt.client as mqtt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

def test_mqtt_role_assignment():
    print("=== MQTT Role Assignment Test ===")
    
    app = QApplication(sys.argv)
    
    # Read settings
    settings = QSettings('sets/settings.ini', QSettings.Format.IniFormat)
    server_address = settings.value('server_address', '')
    server_password = settings.value('server_password', '')
    mqtt_address = settings.value('mqtt_address', '')
    
    topic_prefix = f"{server_address}/{server_password}"
    
    print(f"Topic prefix: '{topic_prefix}'")
    print(f"MQTT broker: {mqtt_address}")
    
    # Test client ID
    test_client_id = f"test-client-{uuid.uuid4().hex[:8]}"
    print(f"Test client ID: {test_client_id}")
    
    messages_received = []
    
    def on_connect(client, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code {rc}")
        if rc == 0:
            # Subscribe to client status topic to receive role assignments
            status_topic = f"{topic_prefix}/client/status"
            client.subscribe(status_topic)
            print(f"Subscribed to: {status_topic}")
            
            # Send registration message (simulating client)
            registration_topic = f"{topic_prefix}/server/status"
            registration_message = f"register|{test_client_id}|TEST-HOSTNAME"
            print(f"\\nSending registration:")
            print(f"  Topic: {registration_topic}")
            print(f"  Message: {registration_message}")
            client.publish(registration_topic, registration_message)
            
        else:
            print(f"Failed to connect with code {rc}")
    
    def on_message(client, userdata, message):
        topic = message.topic
        payload = message.payload.decode('utf-8')
        print(f"\\nReceived message:")
        print(f"  Topic: {topic}")
        print(f"  Payload: {payload}")
        
        messages_received.append((topic, payload))
        
        # Check if this is a role assignment for our test client
        if payload.startswith('role|'):
            parts = payload.split('|', 2)
            if len(parts) > 2:
                client_id = parts[1]
                role = parts[2]
                print(f"  Parsed role assignment - client_id: '{client_id}', role: '{role}'")
                
                if client_id == test_client_id:
                    print(f"  ✅ ROLE ASSIGNMENT FOR TEST CLIENT: {role}")
                    expected_role = "controller"  # First client should be controller
                    if role == expected_role:
                        print(f"  ✅ CORRECT ROLE: Expected {expected_role}, got {role}")
                    else:
                        print(f"  ❌ WRONG ROLE: Expected {expected_role}, got {role}")
                else:
                    print(f"  ℹ️  Role assignment for different client: {client_id}")
        
        elif payload.startswith('status|'):
            parts = payload.split('|', 1)
            if len(parts) > 1:
                status = parts[1]
                print(f"  Server status update: {status}")
    
    def on_disconnect(client, userdata, rc):
        print(f"Disconnected with code {rc}")
    
    # Create MQTT client
    client_kwargs = {"client_id": f"test-{uuid.uuid4().hex[:8]}", "clean_session": False}
    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api is not None:
        version_attr = getattr(callback_api, "VERSION1", None) or getattr(callback_api, "V1", None)
        if version_attr is not None:
            client_kwargs["callback_api_version"] = version_attr
    
    client = mqtt.Client(**client_kwargs)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        print(f"\\nConnecting to {mqtt_address}:1883...")
        client.connect(mqtt_address, 1883, 60)
        client.loop_start()
        
        # Wait for messages
        print("\\nWaiting for server response...")
        time.sleep(10)  # Wait 10 seconds for role assignment
        
        client.loop_stop()
        client.disconnect()
        
        print("\\n=== Test Results ===")
        print(f"Total messages received: {len(messages_received)}")
        
        role_received = False
        for topic, payload in messages_received:
            if payload.startswith('role|') and test_client_id in payload:
                role_received = True
                print(f"✅ Role assignment message received: {payload}")
                break
        
        if not role_received:
            print("❌ No role assignment received for test client")
            print("   This indicates the server is not sending role assignments,")
            print("   or there's an issue with MQTT message delivery.")
            
            print("\\nAll received messages:")
            for i, (topic, payload) in enumerate(messages_received, 1):
                print(f"  {i}. Topic: {topic}")
                print(f"     Payload: {payload}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mqtt_role_assignment()