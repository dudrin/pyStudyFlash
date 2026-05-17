"""
Быстрое исправление для server.py
Заменяет broken _handle_message method
"""

def _handle_message_fixed(self, topic, raw_payload):
    """Исправленный обработчик сообщений"""
    try:
        print(f"Processing message on topic: {topic}")
        client_ref = self.client_mqqt
        if client_ref is None:
            print("No MQTT client reference available")
            return
            
        # Обработка регистрации клиента
        if topic == self.build_topic('server/status'):
            print(f"Processing server/status message")
            payload = raw_payload.decode('utf-8')
            print(f"Server status payload: {payload}")
            
            if payload.startswith('register|'):
                print(f"Client registration request: {payload}")
                parts = payload.split('|', 2)
                client_id = parts[1] if len(parts) > 1 else ''
                display_name = parts[2] if len(parts) > 2 else client_id
                print(f"Registering client - ID: {client_id}, Name: {display_name}")
                self.register_client(client_id, display_name)
                return
                
        # Обработка размера экрана
        elif topic == self.build_topic('server/size'):
            print("Processing server/size request")
            import mss
            with mss.mss() as sct:
                sct_img = sct.grab(sct.monitors[self.monitor])
                size = sct_img.size
                print(f"Sending screen size: {size.width}x{size.height}")
                client_ref.publish(self.build_topic('client/size'), str(size.width) + "|" + str(size.height))
                
        # Обработка запроса первого кадра
        elif topic == self.build_topic('server/update/first'):
            print("Processing first frame request")
            b64img = self.BuildPayload(False)
            client_ref.publish(self.build_topic('client/update/first'), b64img)
            
        # Обработка запроса следующего кадра
        elif topic == self.build_topic('server/update/next'):
            print("Processing next frame request")
            b64img = self.BuildPayload()
            client_ref.publish(self.build_topic('client/update/next'), b64img)
            
        # Обработка отключения клиента
        elif topic == self.build_topic('server/quit'):
            client_id = raw_payload.decode('utf-8').strip()
            print(f"Client disconnect request: {client_id}")
            self.unregister_client(client_id)
            
        else:
            print(f"Unhandled message topic: {topic}")
            
    except Exception as e:
        print(f"Error in _handle_message: {e}")
        import traceback
        traceback.print_exc()

# Инструкции для применения:
# 1. Откройте server.py
# 2. Найдите метод _handle_message
# 3. Замените весь метод на _handle_message_fixed выше
# 4. Переименуйте _handle_message_fixed в _handle_message