#!/usr/bin/env python3
"""
Полный тест соединения сервера и клиента
"""

import sys
import time
import uuid
import paho.mqtt.client as mqtt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

def test_server_client_connection():
    print("=== Тест полного соединения сервер-клиент ===\n")
    
    app = QApplication(sys.argv)
    
    # Читаем настройки
    settings = QSettings('sets/settings.ini', QSettings.Format.IniFormat)
    server_address = str(settings.value('server_address', '', type=str))
    server_password = str(settings.value('server_password', '', type=str))
    mqtt_address = str(settings.value('mqtt_address', '', type=str))
    
    topic_prefix = f"{server_address}/{server_password}"
    
    print(f"Конфигурация:")
    print(f"  Server address: {server_address}")
    print(f"  Server password: {server_password}")
    print(f"  MQTT broker: {mqtt_address}")
    print(f"  Topic prefix: {topic_prefix}\n")
    
    # Проверка настроек
    if not server_address or not mqtt_address:
        print("❌ ОШИБКА: Настройки не заполнены!")
        print("   Проверьте файл sets/settings.ini")
        return False
    
    # ID тестового клиента
    test_client_id = f"test-client-{uuid.uuid4().hex[:8]}"
    test_hostname = "TEST-MACHINE"
    
    messages_received = []
    role_received = None
    screen_size_received = False
    
    def on_connect(client, userdata, flags, rc):
        print(f"✓ Подключено к MQTT брокеру (код: {rc})")
        if rc == 0:
            # Подписываемся на клиентские топики
            client.subscribe(f"{topic_prefix}/client/status")
            client.subscribe(f"{topic_prefix}/client/size")
            client.subscribe(f"{topic_prefix}/client/update/first")
            print("✓ Подписались на топики клиента\n")
            
            # Отправляем регистрацию
            registration_topic = f"{topic_prefix}/server/status"
            registration_msg = f"register|{test_client_id}|{test_hostname}"
            print(f"→ Отправка регистрации:")
            print(f"  Топик: {registration_topic}")
            print(f"  Сообщение: {registration_msg}\n")
            client.publish(registration_topic, registration_msg)
            
            # Запрашиваем размер экрана
            time.sleep(0.5)
            size_topic = f"{topic_prefix}/server/size"
            print(f"→ Запрос размера экрана: {size_topic}\n")
            client.publish(size_topic, "1")
            
    def on_message(client, userdata, message):
        nonlocal role_received, screen_size_received
        
        topic = message.topic
        payload = message.payload.decode('utf-8', errors='ignore')
        
        print(f"← Получено сообщение:")
        print(f"  Топик: {topic}")
        print(f"  Payload: {payload[:100]}...")
        
        messages_received.append((topic, payload))
        
        # Проверяем назначение роли
        if topic == f"{topic_prefix}/client/status":
            if payload.startswith('role|'):
                parts = payload.split('|', 2)
                if len(parts) > 2:
                    client_id = parts[1]
                    role = parts[2]
                    if client_id == test_client_id:
                        role_received = role
                        role_icon = '👑' if role == 'controller' else '👀'
                        print(f"\n{role_icon} РОЛЬ ПОЛУЧЕНА: {role.upper()}\n")
                        
                        # Если controller, запрашиваем первый кадр
                        if role == 'controller':
                            time.sleep(0.5)
                            first_frame_topic = f"{topic_prefix}/server/update/first"
                            print(f"→ Запрос первого кадра: {first_frame_topic}\n")
                            client.publish(first_frame_topic, "1")
        
        # Проверяем размер экрана
        elif topic == f"{topic_prefix}/client/size":
            if '|' in payload:
                width, height = payload.split('|')
                screen_size_received = True
                print(f"\n📐 РАЗМЕР ЭКРАНА: {width}x{height}\n")
        
        # Проверяем получение кадра
        elif topic == f"{topic_prefix}/client/update/first":
            frame_size = len(payload)
            print(f"\n🖼️ ПЕРВЫЙ КАДР ПОЛУЧЕН: {frame_size} байт\n")
    
    def on_disconnect(client, userdata, rc):
        print(f"✗ Отключено от MQTT (код: {rc})")
    
    # Создаем MQTT клиент
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
        print(f"→ Подключение к {mqtt_address}:1883...\n")
        client.connect(mqtt_address, 1883, 60)
        client.loop_start()
        
        # Ждем ответа от сервера
        print("⏳ Ожидание ответа от сервера (15 секунд)...\n")
        time.sleep(15)
        
        client.loop_stop()
        client.disconnect()
        
        # Анализ результатов
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТЫ ТЕСТА")
        print("="*60 + "\n")
        
        print(f"📊 Статистика:")
        print(f"  Получено сообщений: {len(messages_received)}")
        print(f"  Роль получена: {'✓' if role_received else '✗'} {role_received or 'НЕТ'}")
        print(f"  Размер экрана получен: {'✓' if screen_size_received else '✗'}")
        
        print(f"\n📝 Все полученные сообщения:")
        if messages_received:
            for i, (topic, payload) in enumerate(messages_received, 1):
                print(f"  {i}. {topic}")
                print(f"     {payload[:80]}...")
        else:
            print("  (нет сообщений)")
        
        # Оценка результата
        print(f"\n{'='*60}")
        if role_received and screen_size_received:
            print("✅ ТЕСТ ПРОЙДЕН: Соединение работает полностью!")
            if role_received == 'controller':
                print("   → Клиент получил роль CONTROLLER")
                print("   → Можно управлять сервером и видеть экран")
            else:
                print("   → Клиент получил роль VIEWER")
                print("   → Можно только просматривать экран")
            return True
        elif role_received:
            print("⚠️  ЧАСТИЧНЫЙ УСПЕХ: Роль получена, но размер экрана не получен")
            print("   → Возможно сервер не работает")
            return False
        elif len(messages_received) > 0:
            print("⚠️  ЧАСТИЧНЫЙ УСПЕХ: Получены сообщения, но роль не назначена")
            print("   → Проверьте логику назначения ролей на сервере")
            return False
        else:
            print("❌ ТЕСТ НЕ ПРОЙДЕН: Нет ответа от сервера")
            print("   → Убедитесь что:")
            print("     1. Сервер запущен (нажата кнопка 'Старт доступ')")
            print("     2. Сервер подключен к тому же MQTT брокеру")
            print("     3. Используется правильный topic_prefix")
            return False
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_server_client_connection()
    print(f"\n{'='*60}")
    print(f"Результат: {'УСПЕХ ✓' if success else 'НЕУДАЧА ✗'}")
    print(f"{'='*60}\n")
