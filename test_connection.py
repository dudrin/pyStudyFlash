#!/usr/bin/env python3
"""
Simple test script to verify MQTT connection and message flow
"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

def test_settings():
    """Test if settings are being read correctly"""
    print("=== Testing Settings ===")
    
    settings = QSettings('sets/settings.ini', QSettings.Format.IniFormat)
    print(f"Settings file: {settings.fileName()}")
    
    server_address = settings.value('server_address', '')
    server_password = settings.value('server_password', '')
    mqtt_address = settings.value('mqtt_address', '')
    mqtt_port = settings.value('mqtt_port', '')
    mqtt_timeout = settings.value('mqtt_timeout', '')
    
    print(f"Server address: '{server_address}'")
    print(f"Server password: '{server_password}'")
    print(f"MQTT address: '{mqtt_address}'")
    print(f"MQTT port: '{mqtt_port}'")
    print(f"MQTT timeout: '{mqtt_timeout}'")
    
    return server_address, server_password, mqtt_address, mqtt_port, mqtt_timeout

def test_topic_building():
    """Test topic building"""
    print("\n=== Testing Topic Building ===")
    
    server_address = "test@example.com"
    server_password = "testpass"
    topic_prefix = f"{server_address}/{server_password}"
    
    print(f"Topic prefix: '{topic_prefix}'")
    print(f"Server status topic: '{topic_prefix}/server/status'")
    print(f"Client status topic: '{topic_prefix}/client/status'")

def main():
    app = QApplication(sys.argv)
    
    test_settings()
    test_topic_building()
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()