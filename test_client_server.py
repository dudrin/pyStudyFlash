#!/usr/bin/env python3
"""
Тест соединения клиент-сервер для диагностики проблемы
"""

import paho.mqtt.client as mqtt
import time
import uuid
import threading

class MQTTTester:
    def __init__(self, role, client_id=None):
        self.role = role  # 'server' or 'client'
        self.client_id = client_id or f"{role}_{uuid.uuid4().hex[:8]}"
        self.topic_prefix = "dudkate@yandex.ru/123456"
        self.connected = False
        self.messages_received = []
        
        # Setup MQTT client
        client_kwargs = {"client_id": self.client_id, "clean_session": False}
        callback_api = getattr(mqtt, "CallbackAPIVersion", None)
        if callback_api is not None:
            version_attr = getattr(callback_api, "VERSION1", None) or getattr(callback_api, "V1", None)
            if version_attr is not None:
                client_kwargs["callback_api_version"] = version_attr
        
        self.client = mqtt.Client(**client_kwargs)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        
    def build_topic(self, suffix):
        return f"{self.topic_prefix}/{suffix}"
        
    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"[{self.role}] Connected to MQTT broker with code {rc}")
        if rc == 0:
            self.connected = True
            if self.role == 'server':
                # Server subscribes to server/* topics
                topics = ['server/status', 'server/size', 'server/update/first', 'server/update/next']
                for topic in topics:
                    full_topic = self.build_topic(topic)
                    client.subscribe(full_topic)
                    print(f"[{self.role}] Subscribed to: {full_topic}")
            else:
                # Client subscribes to client/* topics
                topics = ['client/status', 'client/size', 'client/update/first', 'client/update/next']
                for topic in topics:
                    full_topic = self.build_topic(topic)
                    client.subscribe(full_topic)
                    print(f"[{self.role}] Subscribed to: {full_topic}")
        else:
            print(f"[{self.role}] Failed to connect with code {rc}")
            
    def on_disconnect(self, client, userdata, rc, properties=None):
        print(f"[{self.role}] Disconnected with code {rc}")
        self.connected = False
        
    def on_message(self, client, userdata, message):
        payload = message.payload.decode('utf-8', errors='ignore')
        print(f"[{self.role}] Received on {message.topic}: {payload[:100]}...")
        self.messages_received.append((message.topic, payload))
        
    def connect(self):
        print(f"[{self.role}] Connecting to broker.hivemq.com:1883...")
        try:
            self.client.connect('broker.hivemq.com', 1883, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[{self.role}] Connection error: {e}")
            return False
            
    def disconnect(self):
        if self.connected:
            self.client.disconnect()
        self.client.loop_stop()
        
    def send_message(self, topic_suffix, payload):
        if self.connected:
            full_topic = self.build_topic(topic_suffix)
            self.client.publish(full_topic, payload)
            print(f"[{self.role}] Sent to {full_topic}: {payload}")
        else:
            print(f"[{self.role}] Cannot send - not connected")

def test_communication():
    print("=== Testing MQTT Communication ===")
    
    # Create server and client testers
    server = MQTTTester('server')
    client = MQTTTester('client')
    
    # Connect both
    if not server.connect():
        print("Server connection failed")
        return
        
    if not client.connect():
        print("Client connection failed") 
        return
        
    # Wait for connections
    time.sleep(2)
    
    print("\n=== Testing Client Registration ===")
    # Client sends registration
    client.send_message('server/status', f'register|{client.client_id}|TestClient')
    
    # Wait for message processing
    time.sleep(2)
    
    print("\n=== Testing Screen Size Request ===")
    # Client requests screen size
    client.send_message('server/size', '1')
    
    # Server responds with size
    server.send_message('client/size', '1920|1080')
    
    # Wait for message processing
    time.sleep(2)
    
    print("\n=== Results ===")
    print(f"Server received {len(server.messages_received)} messages:")
    for topic, payload in server.messages_received:
        print(f"  {topic}: {payload[:50]}...")
        
    print(f"Client received {len(client.messages_received)} messages:")
    for topic, payload in client.messages_received:
        print(f"  {topic}: {payload[:50]}...")
        
    # Cleanup
    client.disconnect()
    server.disconnect()
    
    return len(server.messages_received) > 0 and len(client.messages_received) > 0

if __name__ == "__main__":
    success = test_communication()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")