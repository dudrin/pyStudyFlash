#!/usr/bin/env python3
"""
Test the complete client-server role assignment flow
"""

import sys
import time
import uuid
import paho.mqtt.client as mqtt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

def test_clean_role_assignment():
    print("=== Testing Clean Role Assignment ===")
    
    app = QApplication(sys.argv)
    
    # Read settings
    settings = QSettings('sets/settings.ini', QSettings.Format.IniFormat)
    server_address = settings.value('server_address', '')
    server_password = settings.value('server_password', '')
    mqtt_address = settings.value('mqtt_address', '')
    
    topic_prefix = f"{server_address}/{server_password}"
    
    print(f"Topic prefix: '{topic_prefix}'")
    print(f"MQTT broker: {mqtt_address}")
    
    # Multiple test clients
    test_clients = []
    for i in range(2):
        client_id = f"test-client-{i+1}-{uuid.uuid4().hex[:6]}"
        test_clients.append({
            'id': client_id,
            'name': f"CLIENT-{i+1}",
            'role_received': None
        })
    
    print(f"Test clients: {[c['id'] for c in test_clients]}")
    
    messages_received = []
    
    def on_connect(client, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code {rc}")
        if rc == 0:
            # Subscribe to client status topic
            status_topic = f"{topic_prefix}/client/status"
            client.subscribe(status_topic)
            print(f"Subscribed to: {status_topic}")
            
            # Send registration messages for test clients (simulate multiple clients)
            for i, test_client in enumerate(test_clients):
                registration_topic = f"{topic_prefix}/server/status"
                registration_message = f"register|{test_client['id']}|{test_client['name']}"
                print(f"\\nRegistering client {i+1}:")
                print(f"  Topic: {registration_topic}")
                print(f"  Message: {registration_message}")
                client.publish(registration_topic, registration_message)
                time.sleep(0.5)  # Small delay between registrations
            
        else:
            print(f"Failed to connect with code {rc}")
    
    def on_message(client, userdata, message):
        topic = message.topic
        payload = message.payload.decode('utf-8')
        print(f"\\nReceived message:")
        print(f"  Topic: {topic}")
        print(f"  Payload: {payload}")
        
        messages_received.append((topic, payload))
        
        # Parse role assignments
        if payload.startswith('role|'):
            parts = payload.split('|', 2)
            if len(parts) > 2:
                client_id = parts[1]
                role = parts[2]
                print(f"  Parsed: client_id='{client_id}', role='{role}'")
                
                # Find matching test client
                for test_client in test_clients:
                    if client_id == test_client['id']:
                        test_client['role_received'] = role
                        print(f"  ✅ Role assigned to {test_client['name']}: {role}")
                        break
        
        elif payload.startswith('status|'):
            parts = payload.split('|', 1)
            if len(parts) > 1:
                status = parts[1]
                print(f"  Server status: {status}")
    
    def on_disconnect(client, userdata, rc):
        print(f"Disconnected with code {rc}")
    
    # Create MQTT test client
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
        
        # Wait for role assignments
        print("\\nWaiting for role assignments...")
        time.sleep(8)  # Wait for all role assignments
        
        client.loop_stop()
        client.disconnect()
        
        print("\\n=== ROLE ASSIGNMENT RESULTS ===")
        controller_count = 0
        viewer_count = 0
        
        for test_client in test_clients:
            name = test_client['name']
            role = test_client['role_received']
            if role:
                print(f"{name}: {role.upper()}")
                if role == 'controller':
                    controller_count += 1
                elif role == 'viewer':
                    viewer_count += 1
            else:
                print(f"{name}: NO ROLE RECEIVED ❌")
        
        print(f"\\nSummary:")
        print(f"  Controllers: {controller_count}")
        print(f"  Viewers: {viewer_count}")
        print(f"  Total messages: {len(messages_received)}")
        
        # Verify expected behavior
        expected_controller = 1
        expected_viewers = len(test_clients) - 1
        
        if controller_count == expected_controller and viewer_count == expected_viewers:
            print(f"\\n✅ SUCCESS: Role assignment working correctly!")
            print(f"   - First client got controller role")
            print(f"   - Subsequent clients got viewer roles")
            return True
        else:
            print(f"\\n❌ FAILURE: Role assignment incorrect")
            print(f"   - Expected: {expected_controller} controller, {expected_viewers} viewers")
            print(f"   - Actual: {controller_count} controllers, {viewer_count} viewers")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_clean_role_assignment()
    print(f"\\nTest result: {'PASSED' if success else 'FAILED'}")