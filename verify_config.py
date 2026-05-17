#!/usr/bin/env python3
"""
Configuration verification script to help debug topic prefix issues.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

def main():
    app = QApplication(sys.argv)
    
    print("=== Configuration Verification ===")
    
    # Read settings file
    settings = QSettings('sets/settings.ini', QSettings.Format.IniFormat)
    print(f"Settings file: {settings.fileName()}")
    
    server_address = settings.value('server_address', '')
    server_password = settings.value('server_password', '')
    mqtt_address = settings.value('mqtt_address', '')
    mqtt_port = settings.value('mqtt_port', '')
    mqtt_timeout = settings.value('mqtt_timeout', '')
    
    print(f"\nServer Settings:")
    print(f"  server_address: '{server_address}'")
    print(f"  server_password: '{server_password}'")
    print(f"  mqtt_address: '{mqtt_address}'")
    print(f"  mqtt_port: '{mqtt_port}'")
    print(f"  mqtt_timeout: '{mqtt_timeout}'")
    
    # Calculate topic prefix
    topic_prefix = f"{server_address}/{server_password}"
    print(f"\nTopic Configuration:")
    print(f"  Topic prefix: '{topic_prefix}'")
    print(f"  Server registration topic: '{topic_prefix}/server/status'")
    print(f"  Client status topic: '{topic_prefix}/client/status'")
    
    print(f"\nExpected Client Registration Message:")
    print(f"  Topic: '{topic_prefix}/server/status'")
    print(f"  Payload: 'register|<client_id>|<hostname>'")
    
    print(f"\nExpected Server Response Topic:")
    print(f"  Topic: '{topic_prefix}/client/status'")
    print(f"  Payload: 'status|control' or 'role|<client_id>|controller'")
    
    print("\n=== Recommendations ===")
    if not server_address:
        print("ERROR: server_address is empty! Please configure in settings.")
    if not server_password:
        print("WARNING: server_password is empty! This may cause connection issues.")
    if not mqtt_address:
        print("ERROR: mqtt_address is empty! Please configure MQTT broker.")
    else:
        print("✓ Configuration looks valid")
        print("✓ Make sure both server and client use the SAME topic prefix")
        print("✓ Clear the client input field to use settings file values")

if __name__ == "__main__":
    main()