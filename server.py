import pyautogui
from PyQt6 import QtCore
from PyQt6.QtCore import QTimer, Qt, QEvent
from PyQt6.QtGui import QKeySequence, QCursor, QShortcut
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMdiArea, QMdiSubWindow, QRadioButton, QButtonGroup, QFrame, QApplication
import paho.mqtt.client as mqtt
import queue
import time
import uuid
import mss
import zlib
from functools import partial
import numpy
import base64
import pickle
# import pydirectinput
from pynput import mouse as mouse_move
from pynput.keyboard import Controller, Key
from pynput.mouse import Controller as MouseController
from classes.get_cursor import get_current_cursor
from classes.timer_server import MyTimer

HOTPATH_LOGS = False


def _hotpath_log(message):
    if HOTPATH_LOGS:
        print(message)


class ClientViewerWindow(QMainWindow):
    def __init__(self, client_id, on_close):
        super().__init__()
        self._client_id = client_id
        self._on_close = on_close
        self._fullscreen_mode = False
        self._normal_geometry = None
        self._normal_window_state = Qt.WindowState.WindowNoState
        self._normal_window_flags = self.windowFlags()

        # Top overlay shown only in fullscreen mode.
        self._overlay = QFrame(self)
        self._overlay.setFrameShape(QFrame.Shape.StyledPanel)
        self._overlay.setStyleSheet(
            "QFrame { background: rgba(30, 30, 30, 220); color: white; border: 1px solid #505050; }"
            "QPushButton { background: #444; color: white; border: 1px solid #666; padding: 4px 10px; }"
            "QPushButton:hover { background: #555; }"
        )
        self._overlay_layout = QHBoxLayout(self._overlay)
        self._overlay_layout.setContentsMargins(8, 6, 8, 6)
        self._overlay_layout.setSpacing(8)
        self._overlay_label = QLabel("Fullscreen mode")
        self._overlay_hint = QLabel("Ctrl+Tab to exit")
        self._overlay_exit = QPushButton("Exit Fullscreen")
        self._overlay_exit.clicked.connect(self.exit_fullscreen_mode)
        self._overlay_layout.addWidget(self._overlay_label)
        self._overlay_layout.addStretch(1)
        self._overlay_layout.addWidget(self._overlay_hint)
        self._overlay_layout.addWidget(self._overlay_exit)
        self._overlay.hide()
        self._overlay.raise_()

        self._overlay_hide_timer = QTimer(self)
        self._overlay_hide_timer.setSingleShot(True)
        self._overlay_hide_timer.timeout.connect(self._overlay.hide)

        # Shortcut works when this view has focus.
        self._fullscreen_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        self._fullscreen_shortcut.activated.connect(self.exit_fullscreen_mode)
        self._fullscreen_shortcut.setEnabled(False)

        # Keep this window independent from MDI infrastructure.
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setMouseTracking(True)
        self.installEventFilter(self)

    def setWidget(self, widget):
        old_widget = self.centralWidget()
        if old_widget is not None:
            old_widget.removeEventFilter(self)
        self.setCentralWidget(widget)
        if widget is not None:
            widget.setMouseTracking(True)
            widget.installEventFilter(self)
            notify = getattr(widget, "on_viewer_fullscreen_changed", None)
            if callable(notify):
                notify(self._fullscreen_mode)

    def widget(self):
        return self.centralWidget()

    def is_fullscreen_mode(self):
        return self._fullscreen_mode

    def toggle_fullscreen_mode(self):
        if self._fullscreen_mode:
            self.exit_fullscreen_mode()
        else:
            self.enter_fullscreen_mode()

    def _notify_fullscreen_state(self):
        widget = self.widget()
        if widget is None:
            return
        notify = getattr(widget, "on_viewer_fullscreen_changed", None)
        if callable(notify):
            notify(self._fullscreen_mode)

    def enter_fullscreen_mode(self):
        if self._fullscreen_mode:
            return
        self._fullscreen_mode = True
        self._normal_geometry = self.geometry()
        self._normal_window_state = self.windowState()
        self._normal_window_flags = self.windowFlags()
        screen = QApplication.screenAt(QCursor.pos())
        if screen is not None and self.windowHandle() is not None:
            self.windowHandle().setScreen(screen)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self._fullscreen_shortcut.setEnabled(True)
        self._position_overlay()
        self._show_overlay_temporarily()
        self._notify_fullscreen_state()

    def exit_fullscreen_mode(self):
        if not self._fullscreen_mode:
            return
        self._fullscreen_mode = False
        self._fullscreen_shortcut.setEnabled(False)
        self._overlay_hide_timer.stop()
        self._overlay.hide()
        self.setWindowFlags(self._normal_window_flags)
        self.showNormal()
        if self._normal_window_state == Qt.WindowState.WindowMaximized:
            self.showMaximized()
        elif self._normal_geometry is not None:
            self.setGeometry(self._normal_geometry)
        self.show()
        self.raise_()
        self.activateWindow()
        self._notify_fullscreen_state()

    def _position_overlay(self):
        if not self._overlay.isVisible() and not self._fullscreen_mode:
            return
        width = max(300, self.width() - 24)
        height = 42
        self._overlay.setGeometry(12, 10, width, height)
        self._overlay.raise_()

    def _show_overlay_temporarily(self):
        if not self._fullscreen_mode:
            return
        self._position_overlay()
        self._overlay.show()
        self._overlay.raise_()
        self._overlay_hide_timer.start(1800)

    def _refresh_overlay_hover(self):
        if not self._fullscreen_mode:
            return
        local_pos = self.mapFromGlobal(QCursor.pos())
        if local_pos.y() <= 10:
            self._show_overlay_temporarily()

    def eventFilter(self, watched, event):
        if self._fullscreen_mode and event.type() in {QEvent.Type.MouseMove, QEvent.Type.Enter}:
            self._refresh_overlay_hover()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fullscreen_mode:
            self._position_overlay()

    def keyPressEvent(self, event):
        if self._fullscreen_mode:
            is_ctrl_tab = (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_Tab
            if is_ctrl_tab:
                self.exit_fullscreen_mode()
                event.accept()
                return
        super().keyPressEvent(event)

    def closeEvent(self, closeEvent):
        if self._fullscreen_mode:
            self.exit_fullscreen_mode()
        if callable(self._on_close):
            self._on_close(self._client_id)
        super().closeEvent(closeEvent)


class ScreenShareServer(QMainWindow):
    def __init__(self, app_manager=None):
        super().__init__()
        self.app_manager = app_manager
        self.mqtt_timeout = None
        self.mqtt_address = None
        self.mqtt_port = None
        self.mqtt_username = ''
        self.mqtt_password = ''
        self.mqtt_transport = 'tcp'
        self.mqtt_use_tls = False
        self.mqtt_tls_insecure = False
        self.mqtt_ws_path = '/mqtt'
        self.server_password, self.server_address, self.mqtt_timeout, self.mqtt_address, self.mqtt_port = None, None, None, None, None
        self.connect_mqtt = False  # MQTT connection flag
        self.monitor = 0  # all monitors
        self.quit, self.capture, self.last_image = False, False, None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_screen)

        self.mouse_move_on_server = False
        self.mouse_released = False  # Tracks whether the left mouse button is released
        self.mouse_move = False  # Indicates that the client is moving the mouse
        self.mouse_shift_active = False  # Shift-модификатор для remote drag/click
        self.timer_block_mouse_client = MyTimer(5.0, self.on_timer)  # Timer to block client control when local user moves the mouse
        self.listener = mouse_move.Listener(on_move=self.on_move)
        self.listener.start()

        self.keyboard = Controller()
        self.mouse = MouseController()

        self.setMouseTracking(True)

        self.mouse_label_x, self.mouse_label_y = -1, -1  # Выводим позицию курсора мыши за экран

        self.my_id = str(uuid.uuid4()) + str(time.time())
        print("Client Id = " + self.my_id)
        self.client_mqqt = None
        self.topic_prefix = ''

        self.server_status = "wait"  # wait: idle, send: sharing screen, control: under remote control

        self.clients = {}
        self.client_windows = {}
        self.client_viewers = {}
        self.controller_id = None
        self.controller_button_group = QButtonGroup()  # Группа радиокнопок для выбора контроллера
        self.controller_button_group.buttonClicked.connect(self._on_controller_radio_clicked)
        
        # Initialize UI components
        self.mdi_area = QMdiArea()
        self.setCentralWidget(self.mdi_area)
        self.setWindowTitle('Screen Share Server')
        self._ui_tasks = queue.Queue()

    @QtCore.pyqtSlot()
    def _drain_ui_tasks(self):
        while True:
            try:
                task = self._ui_tasks.get_nowait()
            except queue.Empty:
                break
            try:
                task()
            except Exception as exc:
                print(f"UI task error: {exc}")

    def _run_on_ui(self, callback):
        if QtCore.QThread.currentThread() == self.thread():
            callback()
            return
        self._ui_tasks.put(callback)
        QtCore.QMetaObject.invokeMethod(
            self,
            "_drain_ui_tasks",
            Qt.ConnectionType.QueuedConnection,
        )

    def _on_controller_radio_clicked(self, button):
        client_id = button.property('client_id')
        if client_id and client_id != self.controller_id:
            self.set_controller(client_id)

    def build_topic(self, suffix: str) -> str:
        if self.topic_prefix:
            return f"{self.topic_prefix}/{suffix}"
        return suffix

    def reset_session_state(self):
        """Полный сброс состояния сессии сервера"""
        print("Resetting server session state")
        
        self.quit = False
        self.capture = False
        self.last_image = None
        self.mouse_label_x = -1
        self.mouse_label_y = -1
        self.mouse_released = False
        self.mouse_move = False
        self.mouse_move_on_server = False
        self._release_shift_modifier()
        
        # Останавливаем таймер блокировки мыши
        if hasattr(self, 'timer_block_mouse_client') and self.timer_block_mouse_client is not None:
            self.timer_block_mouse_client.stop()
            
        # Очищаем все окна просмотра клиентов
        for viewer_id, viewer_info in list(self.client_viewers.items()):
            window = viewer_info.get('window')
            if window is not None:
                try:
                    window.close()
                except Exception:
                    pass
        self.client_viewers.clear()
        
        # Сбрасываем статус сервера
        self.server_status = 'wait'
        self.controller_id = None
        
        print("Server session state reset complete")

    def on_move(self, x, y):
        if not hasattr(self, 'mouse_move') or not hasattr(self, 'timer_block_mouse_client'):
            return
        if not self.mouse_move:
            if not self.timer_block_mouse_client.isActive():
                self.mouse_move_on_server = True
                self.timer_block_mouse_client.start()
        self.mouse_move = False

    def on_timer(self):  # Сработал таймер - блокировка управления мышью на сервере для клиента снята
        # print('Сработал таймер', time.time())
        self.timer_block_mouse_client.stop()
        self.mouse_move_on_server = False  # Клиенту разрешено управлять мышью сервера

    def _release_shift_modifier(self):
        if not self.mouse_shift_active:
            return
        try:
            self.keyboard.release(Key.shift)
        except Exception:
            pass
        self.mouse_shift_active = False

    def _parse_mouse_payload(self, payload):
        parts = payload.split('|')
        coords = parts[0].strip().strip('()')
        x_text, y_text = [value.strip() for value in coords.split(',', 1)]
        modifiers = {item.strip().lower() for item in parts[1:] if item.strip()}
        return int(x_text), int(y_text), modifiers

    def on_connect(self, client, userdata, flags, rc):  # Событие подключения к MQTT серверу
        print("Connected flags " + str(flags) + " ,result code=" + str(rc))
        if rc == 0:
            self.connect_mqtt = True  # Есть подключение к MQTT серверу
            
            # КРИТИЧНО: Очищаем старых клиентов при переподключении сервера
            print(f"[DEBUG] Clearing old clients on server reconnect - current clients: {len(self.clients)}")
            if self.clients:
                old_clients = list(self.clients.keys())
                for client_id in old_clients:
                    print(f"[DEBUG] Removing stale client: {client_id}")
                    self.unregister_client(client_id)
                print(f"[DEBUG] Cleared {len(old_clients)} old clients")
            
            # Сбрасываем состояние контроллера
            self.controller_id = None
            self.server_status = 'wait'
            print("[DEBUG] Server state reset - ready for new clients")
        else:
            self.connect_mqtt = False

    def on_disconnect(self, client, userdata, rc, properties=None):  # Событие отключения от MQTT сервера
        """Обработчик отключения сервера от MQTT брокера"""
        was_connected = self.connect_mqtt
        self.connect_mqtt = False
        self._release_shift_modifier()
        
        if rc == 0:
            print('Server cleanly disconnected from MQTT broker')
        else:
            print(f'Server unexpectedly disconnected from MQTT broker - code: {rc}')
            
        # Очищаем состояние клиентов при отключении сервера
        if was_connected:
            print("Cleaning up client connections after server disconnect")
            for client_id, info in list(self.clients.items()):
                info['status'] = 'Server disconnected'
                self.update_client_window(client_id)
                
        # Обновляем статус сервера
        self.server_status = 'wait'

    def _resolve_keyboard_key(self, key_name):
        key_name = (key_name or '').strip().lower()
        aliases = {
            'return': 'enter',
            'pgdown': 'page_down',
            'pgup': 'page_up',
            'numlock': 'num_lock',
            'plus': '+',
        }
        key_name = aliases.get(key_name, key_name)
        if len(key_name) == 1:
            return key_name
        return getattr(Key, key_name, None)

    def _send_keyboard_sequence(self, key_sequence):
        keys = [key for key in key_sequence.split('+') if key]
        if not keys:
            return

        resolved = [self._resolve_keyboard_key(key) for key in keys]
        if any(key is None for key in resolved):
            print(f"Unknown keyboard sequence: {key_sequence}")
            return

        try:
            if len(resolved) == 1:
                key = resolved[0]
                if isinstance(key, str):
                    self.keyboard.type(key)
                else:
                    self.keyboard.press(key)
                    self.keyboard.release(key)
                return

            for key in resolved:
                self.keyboard.press(key)
            time.sleep(0.03)
            for key in reversed(resolved):
                self.keyboard.release(key)
        except Exception as exc:
            print(f"Keyboard input error for '{key_sequence}': {exc}")
        finally:
            for modifier in (
                    Key.ctrl, Key.ctrl_l, Key.ctrl_r,
                    Key.alt, Key.alt_l, Key.alt_r,
                    Key.shift, Key.shift_l, Key.shift_r):
                try:
                    self.keyboard.release(modifier)
                except Exception:
                    pass

    def on_message(self, client, userdata, message):  # Обработка сообщений клиентов
        """Обработка сообщений с префиксами топиков для изоляции серверов"""
        topic = message.topic
        _hotpath_log(f"Server received message on topic: {topic}")
        
        # ОБРАБОТКА С ПРЕФИКСАМИ - КОМБИНИРУЕМ ОРИГИНАЛЬНУЮ ЛОГИКУ С ПРЕФИКСАМИ
        
        # Обработка регистрации клиента
        if topic == self.build_topic('server/status'):
            payload = message.payload.decode('utf-8')
            if payload.startswith('register|'):
                parts = payload.split('|', 2)
                client_id = parts[1] if len(parts) > 1 else ''
                display_name = parts[2] if len(parts) > 2 else client_id
                print(f"Registering client - ID: '{client_id}', Name: '{display_name}'")
                self.register_client(client_id, display_name)
                return
            if payload.startswith('disconnect|'):
                parts = payload.split('|', 1)
                client_id = parts[1] if len(parts) > 1 else ''
                if client_id:
                    print(f"LWT disconnect from client: {client_id}")
                    self.unregister_client(client_id)
                return
        
        if topic == self.build_topic('server/size'):
            with mss.mss() as sct:
                sct_img = sct.grab(sct.monitors[self.monitor])
                size = sct_img.size
                client.publish(self.build_topic('client/size'), str(size.width) + "|" + str(size.height))
                print(f"Sent screen size: {size.width}x{size.height}")

        if topic == self.build_topic('server/keyboard/keypress'):
            key_sequence = message.payload.decode()
            print(topic + " " + str(key_sequence))
            self._send_keyboard_sequence(key_sequence)
        elif topic == self.build_topic('server/keyboard/keyrelease'):
            pass  # Ничего не делаем при отпускании клавиши

        if topic == self.build_topic('server/mouse/right_click'):
            x, y = map(int, message.payload.decode()[1:-1].split(', '))
            pyautogui.rightClick(x, y)
        elif topic == self.build_topic('server/mouse/left_click'):
            x, y, modifiers = self._parse_mouse_payload(message.payload.decode())
            if 'shift' in modifiers and not self.mouse_shift_active:
                self.keyboard.press(Key.shift)
                self.mouse_shift_active = True
            pyautogui.mouseDown(x, y)
        elif topic == self.build_topic('server/mouse/double_click'):
            x, y = map(int, message.payload.decode()[1:-1].split(', '))
            print("DbClick")
            pyautogui.doubleClick(x, y)
        elif topic == self.build_topic('server/mouse/wheel'):
            steps = int(float(message.payload.decode().split(' ')[0]))
            pyautogui.scroll(steps * 100)

        if topic == self.build_topic('server/mouse/drag_start'):
            self.mouse_released = False
        elif topic == self.build_topic('server/mouse/drag_end'):
            self.mouse_released = True
            pyautogui.mouseUp()
            self._release_shift_modifier()

        if topic == self.build_topic('server/mouse/move'):
            self.mouse_move = True

        if topic == self.build_topic('server/update/first'):
            _hotpath_log(f"[DEBUG] Processing first frame request...")
            with mss.mss() as sct:
                b64img = self.BuildPayload(False)
                client.publish(self.build_topic('client/update/first'), b64img)
                _hotpath_log("Sent first frame")

        if topic == self.build_topic('server/update/next'):
            with mss.mss() as sct:
                b64img = self.BuildPayload()
                client.publish(self.build_topic('client/update/next'), b64img)
                _hotpath_log("Sent next frame")

        if topic == self.build_topic('server/mouse/position'):
            # Получите текущее положение курсора мыши
            x, y = pyautogui.position()
            cursor_type = get_current_cursor()
            if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(cursor_type, str):
                client.publish(self.build_topic('client/mouse/position'), str(x) + "|" + str(y) + "|" + cursor_type)

        if topic == self.build_topic('server/mouse/label'):
            str_mouse_position = message.payload.decode("utf-8")
            str_list = str_mouse_position.split("|")
            self.mouse_label_x = int(str_list[0])
            self.mouse_label_y = int(str_list[1])
            
            if self.mouse_label_x >= 0 and self.mouse_label_y >= 0 and self.mouse_move and not self.mouse_move_on_server:
                self.mouse.position = (self.mouse_label_x, self.mouse_label_y)
                cursor_type = get_current_cursor()
                if isinstance(self.mouse_label_x, (int, float)) and isinstance(self.mouse_label_y, (int, float)) and isinstance(cursor_type, str):
                    client.publish(self.build_topic('client/mouse/position'), str(self.mouse_label_x) + "|" + str(
                        self.mouse_label_y) + "|" + cursor_type + "|next")
            else:
                x, y = self.mouse.position
                cursor_type = get_current_cursor()
                if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(cursor_type, str):
                    client.publish(self.build_topic('client/mouse/position'), str(x) + "|" + str(y) + "|" + cursor_type + "|last")
            self.mouse_label_x, self.mouse_label_y = -1, -1

        if topic == self.build_topic('server/quit'):
            client_id = message.payload.decode('utf-8').strip()
            print(f"Client disconnect request: {client_id}")
            self.unregister_client(client_id)

    def _handle_message(self, topic, raw_payload):
        """ИНТЕГРИРОВАННЫЙ обработчик сообщений на основе util/server_20231123.py"""
        try:
            _hotpath_log(f"Processing message on topic: {topic}")
            client_ref = self.client_mqqt
            if client_ref is None:
                print("ERROR: No MQTT client reference available")
                return
                
            # КРИТИКО: Проверяем наличие активных клиентов для событий мыши/клавиатуры
            mouse_keyboard_topics = [
                'server/mouse/position', 'server/mouse/label', 'server/mouse/right_click',
                'server/mouse/left_click', 'server/mouse/double_click', 'server/mouse/wheel',
                'server/mouse/drag_start', 'server/mouse/move', 'server/mouse/drag_end',
                'server/keyboard/keypress', 'server/keyboard/keyrelease'
            ]
            
            topic_suffix = topic.replace(f"{self.topic_prefix}/", "") if self.topic_prefix else topic
            
            if topic_suffix in mouse_keyboard_topics and not self.has_active_clients():
                print(f"Пропускаем событие {topic_suffix} - нет активных клиентов")
                return
                
            # Обработка регистрации клиента
            if topic == self.build_topic('server/status'):
                payload = raw_payload.decode('utf-8')
                if payload.startswith('register|'):
                    parts = payload.split('|', 2)
                    client_id = parts[1] if len(parts) > 1 else ''
                    display_name = parts[2] if len(parts) > 2 else client_id
                    print(f"Registering client - ID: '{client_id}', Name: '{display_name}'")
                    self.register_client(client_id, display_name)
                    return
                if payload.startswith('disconnect|'):
                    parts = payload.split('|', 1)
                    client_id = parts[1] if len(parts) > 1 else ''
                    if client_id:
                        print(f"LWT disconnect from client: {client_id}")
                        self.unregister_client(client_id)
                    return
                    
            # ИСПОЛЬЗУЕМ ОРИГИНАЛЬНУЮ ЛОГИКУ ИЗ util/server_20231123.py
            
            if topic == self.build_topic('server/size'):
                with mss.mss() as sct:
                    sct_img = sct.grab(sct.monitors[self.monitor])
                    size = sct_img.size
                    client_ref.publish(self.build_topic('client/size'), str(size.width) + "|" + str(size.height))

            if topic == self.build_topic('server/keyboard/keypress'):
                key_sequence = raw_payload.decode()
                print(topic + " " + str(key_sequence))
                self._send_keyboard_sequence(key_sequence)
            elif topic == self.build_topic('server/keyboard/keyrelease'):
                pass  # Ничего не делаем при отпускании клавиши

            if topic == self.build_topic('server/mouse/right_click'):
                x, y = map(int, raw_payload.decode()[1:-1].split(', '))
                pyautogui.rightClick(x, y)
            elif topic == self.build_topic('server/mouse/left_click'):
                x, y, modifiers = self._parse_mouse_payload(raw_payload.decode())
                if 'shift' in modifiers and not self.mouse_shift_active:
                    self.keyboard.press(Key.shift)
                    self.mouse_shift_active = True
                pyautogui.mouseDown(x, y)
            elif topic == self.build_topic('server/mouse/double_click'):
                x, y = map(int, raw_payload.decode()[1:-1].split(', '))
                print("DbClick")
                pyautogui.doubleClick(x, y)
            elif topic == self.build_topic('server/mouse/wheel'):
                steps = int(float(raw_payload.decode().split(' ')[0]))
                # print(steps)
                pyautogui.scroll(steps * 100)

            if topic == self.build_topic('server/mouse/drag_start'):
                self.mouse_released = False
            elif topic == self.build_topic('server/mouse/drag_end'):
                self.mouse_released = True
                pyautogui.mouseUp()
                self._release_shift_modifier()

            if topic == self.build_topic('server/mouse/move'):
                self.mouse_move = True

            if topic == self.build_topic('server/update/first'):
                with mss.mss() as sct:
                    b64img = self.BuildPayload(False)
                    # Отправляем CONTROLLER-у прямое обновление
                    client_ref.publish(self.build_topic('client/update/first'), b64img)
                    _hotpath_log("Sent first frame to controller")
                    
                    # Публикуем тот же кадр в stream для VIEWER-ов
                    if self.has_viewer_clients():
                        client_ref.publish(self.build_topic('client/stream/first'), b64img)
                        print("Broadcasted first frame to viewers")

            if topic == self.build_topic('server/update/next'):
                with mss.mss() as sct:
                    b64img = self.BuildPayload()
                    # Отправляем CONTROLLER-у прямое обновление
                    client_ref.publish(self.build_topic('client/update/next'), b64img)
                    _hotpath_log("Sent next frame to controller")
                    
                    # Публикуем тот же кадр в stream для VIEWER-ов
                    if self.has_viewer_clients():
                        client_ref.publish(self.build_topic('client/stream/next'), b64img)
                        print("Broadcasted next frame to viewers")

            if topic == self.build_topic('server/mouse/position'):
                with mss.mss() as sct:
                    # Получите текущее положение курсора мыши
                    x, y = pyautogui.position()
                    # Получаем текущий тип курсора
                    cursor_type = get_current_cursor()
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(cursor_type, str):
                        client_ref.publish(self.build_topic('client/mouse/position'), str(x) + "|" + str(y) + "|" + cursor_type)

            if topic == self.build_topic('server/mouse/label'):  # Предполагаемые позиции мыши с клиента управления для отображения курсора
                str_mouse_position = raw_payload.decode("utf-8")
                str_list = str_mouse_position.split("|")
                self.mouse_label_x = int(str_list[0])
                self.mouse_label_y = int(str_list[1])
                # print(self.mouse_label_x, '!', self.mouse_label_y, '!', 'self.mouse_move ', self.mouse_move, 'self.mouse_move_on_server ', self.mouse_move_on_server)
                if self.mouse_label_x >= 0 and self.mouse_label_y >= 0 and self.mouse_move and not self.mouse_move_on_server:
                    # pyautogui.moveTo(self.mouse_label_x, self.mouse_label_y)
                    self.mouse.position = (self.mouse_label_x, self.mouse_label_y)
                    cursor_type = get_current_cursor()
                    if isinstance(self.mouse_label_x, (int, float)) and isinstance(self.mouse_label_y, (int, float)) and isinstance(cursor_type, str):
                        client_ref.publish(self.build_topic('client/mouse/position'), str(self.mouse_label_x) + "|" + str(
                            self.mouse_label_y) + "|" + cursor_type + "|next")
                else:
                    # Получите текущее положение курсора мыши
                    # x, y = pyautogui.position()
                    x, y = self.mouse.position
                    cursor_type = get_current_cursor()
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(cursor_type, str):
                        client_ref.publish(self.build_topic('client/mouse/position'), str(x) + "|" + str(y) + "|" + cursor_type + "|last")
                self.mouse_label_x, self.mouse_label_y = -1, -1
                
            # Обработка отключения клиента
            if topic == self.build_topic('server/quit'):
                client_id = raw_payload.decode('utf-8').strip()
                print(f"Client disconnect request: {client_id}")
                self.unregister_client(client_id)
                
        except Exception as e:
            print(f"ERROR in _handle_message: {e}")
            import traceback
            traceback.print_exc()

    def register_client(self, client_id, display_name):
        """Регистрация клиента с поддержкой множественных подключений"""
        if QtCore.QThread.currentThread() != self.thread():
            self._run_on_ui(lambda cid=client_id, name=display_name: self.register_client(cid, name))
            return
        print(f"[DEBUG] register_client called - client_id: '{client_id}', display_name: '{display_name}'")
        print(f"[DEBUG] Before registration - current clients: {len(self.clients)}, controller: {self.controller_id}")
        
        if not client_id:
            print(f"[DEBUG] Empty client_id, returning")
            return
            
        # КРИТИЧНО: Предотвращаем саморегистрацию сервера
        if client_id == self.my_id:
            print(f"[DEBUG] ❌ BLOCKED: Server tried to register itself as client! my_id: {self.my_id}")
            return
            
        display_name = display_name or client_id
        now = time.time()
        
        # Проверяем существование клиента
        existing_info = self.clients.get(client_id)
        is_new_client = existing_info is None
        is_reconnection = existing_info is not None
        
        print(f"[DEBUG] Client analysis - is_new: {is_new_client}, is_reconnection: {is_reconnection}")
        
        if is_new_client:
            # Новый клиент
            info = {
                'name': display_name,
                'status': 'Connected',
                'connected_at': now,
                'last_register_at': now,
                'role': 'viewer',  # По умолчанию все новые клиенты - наблюдатели
                'connection_count': 1
            }
            self.clients[client_id] = info
            
            # Создаем окно управления клиентом
            self.create_client_window(client_id, display_name)
            print(f'📥 NEW CLIENT: {display_name} ({client_id})')
            
        else:
            # Повторное подключение существующего клиента
            previous_register_at = existing_info.get('last_register_at', 0.0)
            duplicate_burst = (now - previous_register_at) < 1.5
            existing_info['name'] = display_name  # Обновляем имя если изменилось
            existing_info['status'] = 'Connected'
            existing_info['connected_at'] = now  # Обновляем время подключения
            existing_info['last_register_at'] = now
            existing_info['connection_count'] = existing_info.get('connection_count', 0) + 1
            
            # Обновляем окно управления клиентом
            self.update_client_window(client_id, display_name)
            print(f'🔄 RECONNECTION: {display_name} ({client_id}) - попытка #{existing_info["connection_count"]}')

            if duplicate_burst:
                print(f"[DEBUG] Duplicate register burst suppressed for {client_id}")
                return
            
        # КРИТИЧЕСКИ ВАЖНО: Назначение ролей
        print(f"[DEBUG] Before role assignment - controller: {self.controller_id}, total clients: {len(self.clients)}")
        self._assign_roles_for_multiple_clients()
        print(f"[DEBUG] After role assignment - controller: {self.controller_id}")
        
        # Рассылаем обновленные роли всем клиентам
        print(f"[DEBUG] Broadcasting roles to all clients")
        self.broadcast_roles()
        
        # Выводим статистику подключений
        total_clients = len(self.clients)
        controller_name = self.clients.get(self.controller_id, {}).get('name', 'None') if self.controller_id else 'None'
        print(f'📊 CLIENTS STATUS: Total={total_clients}, Controller={controller_name}')
        
    def _assign_roles_for_multiple_clients(self):
        """Назначение ролей с приоритетом первого подключившегося клиента"""
        print(f"[DEBUG] _assign_roles_for_multiple_clients called")
        print(f"[DEBUG] Current state - clients: {len(self.clients)}, controller_id: {self.controller_id}")
        
        if not self.clients:
            print(f"[DEBUG] No clients, setting controller_id to None")
            self.controller_id = None
            return
            
        # Если нет активного контроллера или он отключился
        if not self.controller_id or self.controller_id not in self.clients:
            print(f"[DEBUG] No valid controller, finding earliest client")
            # Находим самого раннего клиента по времени подключения
            earliest_client = min(
                self.clients.items(), 
                key=lambda item: item[1].get('connected_at', 0)
            )
            
            old_controller = self.controller_id
            self.controller_id = earliest_client[0]
            
            print(f'[DEBUG] 👑 CONTROLLER ASSIGNMENT: {earliest_client[1].get("name", earliest_client[0])} (first connected)')
            print(f'[DEBUG] Controller changed from {old_controller} to {self.controller_id}')
            
            if old_controller and old_controller != self.controller_id:
                print(f'[DEBUG] 🔄 Controller changed from {old_controller} to {self.controller_id}')
        else:
            print(f"[DEBUG] Controller {self.controller_id} is still valid")
                
        # Устанавливаем роли всех клиентов
        print(f"[DEBUG] Setting roles for all clients:")
        for client_id, info in self.clients.items():
            old_role = info.get('role', 'unknown')
            if client_id == self.controller_id:
                info['role'] = 'controller'
                print(f"[DEBUG]   {client_id} -> CONTROLLER (was {old_role})")
            else:
                info['role'] = 'viewer'
                print(f"[DEBUG]   {client_id} -> VIEWER (was {old_role})")
                
        # Обновляем статус сервера
        old_status = self.server_status
        self.server_status = 'control' if self.controller_id else 'wait'
        print(f"[DEBUG] Server status changed from '{old_status}' to '{self.server_status}'")

    def unregister_client(self, client_id):
        """Полное отключение и очистка клиента"""
        if QtCore.QThread.currentThread() != self.thread():
            self._run_on_ui(lambda cid=client_id: self.unregister_client(cid))
            return
        if not client_id:
            return
            
        info = self.clients.get(client_id)
        if info is None:
            print(f"Client {client_id} not found for unregistration")
            return
        
        print(f'Client disconnecting: {info.get("name", client_id)} ({client_id})')
        
        # Закрываем окно просмотра клиента
        viewer_info = self.client_viewers.get(client_id)
        if viewer_info:
            try:
                window = viewer_info.get('window')
                if window:
                    window.close()
                    print(f"Closed viewer window for client {client_id}")
            except Exception as e:
                print(f"Error closing viewer window: {e}")
                
        # Очищаем список просмотрщиков
        self.client_viewers.pop(client_id, None)
                
        # Обновляем статус клиента
        info['status'] = 'Disconnected'
        self.update_client_window(client_id)
        
        # Откладываем удаление окна клиента на 3 секунды
        QTimer.singleShot(3000, lambda: self.remove_client_window(client_id))
        
        # Удаляем клиента из списка
        self.clients.pop(client_id, None)
        
        # Переназначаем контроллера если это был текущий контроллер
        if self.controller_id == client_id:
            old_controller = self.controller_id
            self.controller_id = self._next_controller_id(exclude=client_id)
            if self.controller_id:
                print(f'Controller role transferred from {old_controller} to {self.controller_id}')
            else:
                print('No controller available after disconnection')
                
        # Обновляем роли всех оставшихся клиентов
        self.broadcast_roles()
        self._release_shift_modifier()
        
        # КРИТИКО: Останавливаем отправку событий мыши/клавиатуры если нет клиентов
        if not self.has_active_clients():
            print("Нет активных клиентов - останавливаем отправку событий мыши/клавиатуры")
            self.server_status = 'wait'  # Возвращаемся в режим ожидания
            
        print(f"Client {client_id} fully unregistered")

    def set_controller(self, client_id):
        if client_id not in self.clients:
            print(f'Cannot set controller: client {client_id} not found')
            return
        if self.controller_id == client_id:
            print(f'Client {client_id} is already the controller')
            return
        
        old_controller = self.controller_id
        self.controller_id = client_id
        
        client_name = self.clients[client_id].get('name', client_id)
        old_name = self.clients[old_controller].get('name', old_controller) if old_controller in self.clients else old_controller
        
        print(f'Controller changed from {old_name} to {client_name}')
        self.broadcast_roles()

    def toggle_controller(self, client_id):
        if client_id not in self.clients:
            return
        if self.controller_id == client_id:
            replacement = self._next_controller_id(exclude=client_id)
            self.controller_id = replacement
            self.broadcast_roles()
        else:
            self.set_controller(client_id)

    def _next_controller_id(self, exclude=None):
        if not self.clients:
            return None
        sorted_clients = sorted(self.clients.items(), key=lambda item: item[1].get('connected_at', 0))
        for client_id, _ in sorted_clients:
            if client_id != exclude:
                return client_id
        return None

    def broadcast_roles(self):
        """Обновленная рассылка ролей для множественных клиентов"""
        print(f"[DEBUG] broadcast_roles called - controller: {self.controller_id}, clients: {len(self.clients)}")
        
        # Проверяем состояние контроллера
        if self.controller_id and self.controller_id not in self.clients:
            print(f"[DEBUG] Controller {self.controller_id} not in clients, reassigning")
            self.controller_id = self._next_controller_id()
            
        if not self.clients:
            print(f"[DEBUG] No clients, setting controller to None")
            self.controller_id = None
            self.server_status = 'wait'
        else:
            self.server_status = 'control' if self.controller_id else 'wait'
            
        # Обновляем статус сервера
        print(f"[DEBUG] Publishing server status: {self.server_status}")
        self.publish_server_status()
        
        # Отправляем роль каждому клиенту
        print(f"[DEBUG] Sending roles to {len(self.clients)} clients:")
        for client_id, info in self.clients.items():
            role = 'controller' if client_id == self.controller_id else 'viewer'
            info['role'] = role
            info.setdefault('status', 'Connected')
            
            print(f"[DEBUG] Client {client_id} -> assigning role: {role}")
            
            if self.client_mqqt:
                try:
                    role_message = f"role|{client_id}|{role}"
                    topic = self.build_topic('client/status')
                    result = self.client_mqqt.publish(topic, role_message)
                    
                    client_name = info.get('name', client_id)
                    role_icon = '👑' if role == 'controller' else '👀'
                    print(f'[DEBUG] {role_icon} ROLE SENT: {client_name} -> {role.upper()} | Topic: {topic} | Message: {role_message} | Result: {result}')
                    
                except Exception as e:
                    print(f'[DEBUG] Failed to send role to {client_id}: {e}')
            else:
                print(f"[DEBUG] No MQTT client available to send role to {client_id}")
                    
            self.update_client_window(client_id)
            
        controller_name = self.clients.get(self.controller_id, {}).get('name', 'None') if self.controller_id else 'None'
        viewer_count = len(self.clients) - (1 if self.controller_id else 0)
        print(f'[DEBUG] 📊 BROADCAST COMPLETE: Controller={controller_name}, Viewers={viewer_count}')

    def publish_server_status(self):
        if not self.client_mqqt:
            print("Cannot publish server status - no MQTT client")
            return
        status_message = f"status|{self.server_status}"
        print(f"Publishing server status: {status_message}")
        try:
            self.client_mqqt.publish(self.build_topic('client/status'), status_message)
        except Exception as e:
            print(f"Error publishing server status: {e}")

    def create_client_window(self, client_id, display_name):
        if QtCore.QThread.currentThread() != self.thread():
            self._run_on_ui(lambda cid=client_id, name=display_name: self.create_client_window(cid, name))
            return
        panel = QWidget()
        layout = QVBoxLayout(panel)
        panel.setMinimumSize(320, 250)  # Увеличил высоту для радиокнопки
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        name_label = QLabel(f"Client: {display_name}")
        id_label = QLabel(f"ID: {client_id}")
        role_label = QLabel("Role: Viewer")
        status_label = QLabel("Status: Connected")
        
        # Радиокнопка для выбора контроллера
        controller_radio = QRadioButton("Controller")
        controller_radio.setProperty('client_id', client_id)
        self.controller_button_group.addButton(controller_radio)
        
        controller_button = QPushButton("Make Controller")
        controller_button.setObjectName('controllerButton')
        controller_button.clicked.connect(partial(self.toggle_controller, client_id))
        
        disconnect_button = QPushButton("Disconnect")
        disconnect_button.setObjectName('disconnectButton')
        disconnect_button.clicked.connect(partial(self.disconnect_client, client_id))
        
        view_button = QPushButton("View")
        view_button.setObjectName('viewButton')
        view_button.clicked.connect(partial(self.view_client_screen, client_id))
        
        layout.addWidget(name_label)
        layout.addWidget(id_label)
        layout.addWidget(role_label)
        layout.addWidget(status_label)
        layout.addWidget(controller_radio)  # Добавляем радиокнопку
        
        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addStretch(1)
        button_row.addWidget(controller_button)
        button_row.addWidget(disconnect_button)
        button_row.addWidget(view_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        
        panel.setLayout(layout)
        
        subwindow = QMdiSubWindow()
        subwindow.setWidget(panel)
        subwindow.setWindowTitle(display_name)
        self.mdi_area.addSubWindow(subwindow)
        subwindow.show()
        
        self.client_windows[client_id] = {
            'window': subwindow,
            'panel': panel,
            'name_label': name_label,
            'id_label': id_label,
            'role_label': role_label,
            'status_label': status_label,
            'controller_radio': controller_radio,
            'controller_button': controller_button,
            'disconnect_button': disconnect_button,
            'view_button': view_button
        }

    def update_client_window(self, client_id, display_name=None):
        if QtCore.QThread.currentThread() != self.thread():
            self._run_on_ui(lambda cid=client_id, name=display_name: self.update_client_window(cid, name))
            return
        data = self.client_windows.get(client_id)
        info = self.clients.get(client_id)
        if not data or not info:
            return
            
        name = display_name or info.get('name', client_id)
        connection_count = info.get('connection_count', 1)
        data['name_label'].setText(f"Client: {name} (#{connection_count})")
        
        if 'id_label' in data:
            data['id_label'].setText(f"ID: {client_id}")
            
        role = info.get('role', 'viewer')
        role_text = 'Controller' if role == 'controller' else 'Viewer'
        
        # Добавляем статистику количества клиентов
        total_clients = len(self.clients)
        if role == 'controller':
            role_text += f" (1 of {total_clients})"
        else:
            viewer_position = list(self.clients.keys()).index(client_id) 
            role_text += f" ({viewer_position + 1} of {total_clients})"
            
        data['role_label'].setText(f"Role: {role_text}")
        
        status_text = info.get('status', 'Connected')
        data['status_label'].setText(f"Status: {status_text}")
        
        # Обновляем радиокнопку
        controller_radio = data.get('controller_radio')
        if controller_radio is not None:
            controller_radio.setChecked(role == 'controller')
            controller_radio.setText(f"Controller ({name})")
        
        controller_button = data.get('controller_button')
        if controller_button is not None:
            if role == 'controller':
                controller_button.setText('Revoke Control')
            else:
                controller_button.setText('Make Controller')
            controller_button.setEnabled(True)
            
        disconnect_button = data.get('disconnect_button')
        if disconnect_button is not None:
            disconnect_button.setEnabled(info.get('status') not in {'Disconnecting', 'Disconnected'})
            
        view_button = data.get('view_button')
        if view_button is not None:
            if self.app_manager and hasattr(self.app_manager, 'get_address_book_entry'):
                entry = self.app_manager.get_address_book_entry(name) or self.app_manager.get_address_book_entry(client_id)
                view_button.setEnabled(entry is not None)
            else:
                view_button.setEnabled(False)
                
        window = data.get('window')
        if window is not None:
            title = name if role != 'controller' else f"{name} [Controller]"
            window.setWindowTitle(title)

    def disconnect_client(self, client_id):
        info = self.clients.get(client_id)
        if not info:
            return
        if self.client_mqqt:
            try:
                self.client_mqqt.publish(self.build_topic('client/status'), f"command|{client_id}|disconnect")
            except Exception:
                pass
        info['status'] = 'Disconnecting'
        viewer_info = self.client_viewers.get(client_id)
        if viewer_info:
            viewer_info['window'].close()
        if self.controller_id == client_id:
            self.controller_id = self._next_controller_id(exclude=client_id)
        self.update_client_window(client_id)
        self.broadcast_roles()

    def view_client_screen(self, client_id):
        info = self.clients.get(client_id)
        if not info:
            return
        if client_id in self.client_viewers:
            existing = self.client_viewers[client_id]['window']
            existing.showNormal()
            existing.raise_()
            existing.activateWindow()
            return
        display_name = info.get('name', client_id)
        entry = None
        if self.app_manager and hasattr(self.app_manager, 'get_address_book_entry'):
            entry = self.app_manager.get_address_book_entry(display_name)
            if entry is None:
                entry = self.app_manager.get_address_book_entry(client_id)
        if not entry:
            info['status'] = 'No address entry'
            self.update_client_window(client_id)
            print(f'Address book entry not found for {display_name}')
            return
        info['status'] = 'Connecting'
        self.update_client_window(client_id)
        placeholder = QWidget()
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.setContentsMargins(20, 20, 20, 20)
        placeholder_label = QLabel(f"Connecting to {display_name}...")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addStretch(1)
        placeholder_layout.addWidget(placeholder_label, 0, Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addStretch(1)
        subwindow = ClientViewerWindow(client_id, self._on_viewer_closed)
        subwindow.setWidget(placeholder)
        subwindow.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        subwindow.setWindowTitle(f"{display_name} [View]")
        subwindow.resize(900, 600)
        subwindow.show()
        self.client_viewers[client_id] = {'window': subwindow, 'viewer': None}

        def start_viewer():
            try:
                from client import ScreenShareClient
                viewer = ScreenShareClient()
                viewer.server_address = entry.get('server_address', '')
                viewer.server_password = entry.get('password', '')
                viewer.mqtt_address = entry.get('mqtt_address', '')
                viewer.mqtt_port = entry.get('mqtt_port', 0)
                viewer.mqtt_timeout = entry.get('mqtt_timeout', 0)
                if self.app_manager and hasattr(self.app_manager, 'settings'):
                    settings = self.app_manager.settings
                    viewer.mqtt_username = str(settings.value('mqtt_username', '', type=str) or '').strip()
                    viewer.mqtt_password = str(settings.value('mqtt_password', '', type=str) or '')
                    viewer.mqtt_transport = str(settings.value('mqtt_transport', 'tcp', type=str) or 'tcp').strip().lower()
                    viewer.mqtt_use_tls = str(settings.value('mqtt_use_tls', False)).strip().lower() in {'1', 'true', 'yes', 'on'}
                    viewer.mqtt_tls_insecure = str(settings.value('mqtt_tls_insecure', False)).strip().lower() in {'1', 'true', 'yes', 'on'}
                    viewer.mqtt_ws_path = str(settings.value('mqtt_ws_path', '/mqtt', type=str) or '/mqtt').strip() or '/mqtt'
                bind_viewer_window = getattr(viewer, 'set_viewer_window', None)
                if callable(bind_viewer_window):
                    bind_viewer_window(subwindow)
                subwindow.setWidget(viewer)
                if callable(bind_viewer_window):
                    bind_viewer_window(subwindow)
                viewer.start_stream()
                self.client_viewers[client_id] = {'window': subwindow, 'viewer': viewer}
                info['status'] = 'Viewing'
                self.update_client_window(client_id)
            except Exception as exc:
                info['status'] = 'View error'
                self.update_client_window(client_id)
                print(f"Ошибка при открытии просмотра {display_name}: {exc}")
                subwindow.close()

        QTimer.singleShot(0, start_viewer)

    def _on_viewer_closed(self, client_id):
        viewer_info = self.client_viewers.pop(client_id, None)
        if not viewer_info:
            return
        viewer = viewer_info.get('viewer')
        if viewer is not None:
            try:
                viewer.stop_stream()
            except Exception:
                pass
        info = self.clients.get(client_id)
        if info and info.get('status') == 'Viewing':
            info['status'] = 'Connected'
            self.update_client_window(client_id)

    def remove_client_window(self, client_id):
        """Полное удаление окна клиента и очистка ресурсов"""
        if QtCore.QThread.currentThread() != self.thread():
            self._run_on_ui(lambda cid=client_id: self.remove_client_window(cid))
            return
        data = self.client_windows.pop(client_id, None)
        if not data:
            print(f"No window data found for client {client_id}")
            return
            
        print(f"Removing window for client {client_id}")
            
        # Удаляем радиокнопку из группы
        controller_radio = data.get('controller_radio')
        if controller_radio is not None:
            try:
                self.controller_button_group.removeButton(controller_radio)
                print(f"Removed controller radio button for client {client_id}")
            except Exception as e:
                print(f"Error removing controller radio button: {e}")
            
        # Закрываем окно клиента
        window = data.get('window')
        if window is not None:
            try:
                self.mdi_area.removeSubWindow(window)
                window.close()
                print(f"Closed and removed window for client {client_id}")
            except Exception as e:
                print(f'Error closing client window {client_id}: {e}')
                
        # Очищаем ссылки на все компоненты
        for key in data:
            data[key] = None
            
        print(f"Client window {client_id} fully removed")

    def BuildPayload(self, next_frame=True):  # Передача изображения рабочего стола
        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[self.monitor])
            image = numpy.array(sct_img)
            if next_frame:  # Для следующих изображений только изменения
                xor_image = image ^ self.last_image
                b64img = base64.b64encode(zlib.compress(pickle.dumps(xor_image), 9))
            else:
                b64img = base64.b64encode(zlib.compress(pickle.dumps(image), 9))
            self.last_image = image
            return b64img

    # def BuildPayload(self, next_frame=True):
    #     with mss.mss() as sct:
    #         sct_img = sct.grab(sct.monitors[self.monitor])
    #         image = numpy.array(sct_img)
    #         if next_frame:
    #             xor_image = image ^ self.last_image
    #             b64img = base64.b64encode(zlib.compress(xor_image.tobytes(), 2))
    #         else:
    #             b64img = base64.b64encode(zlib.compress(image.tobytes(), 2))
    #         self.last_image = image
    #         return b64img

    def run(self, server_address='address@mail.com', server_password='', mqtt_address='', mqtt_port=0, mqtt_timeout=0):
        """ИСПРАВЛЕННЫЙ МЕТОД С ПОДДЕРЖКОЙ ПРЕФИКСОВ ТОПИКОВ"""
        self.server_address = server_address
        self.server_password = server_password
        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port
        self.mqtt_timeout = mqtt_timeout
        
        address = (self.server_address or '').strip()
        password = (self.server_password or '').strip()
        
        if not address:
            print('Server address not configured')
            return
            
        if not self.mqtt_address:
            print('MQTT broker address not configured')
            return
            
        # СОЗДАЕМ ПРЕФИКС ТОПИКА ИЗ АДРЕСА И ПАРОЛЯ СЕРВЕРА
        self.topic_prefix = f"{address}/{password}"
        print(f"Using topic prefix: {self.topic_prefix}")

        def _to_bool(value):
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return value != 0
            return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}

        mqtt_username = str(getattr(self, 'mqtt_username', '') or '').strip()
        mqtt_password = str(getattr(self, 'mqtt_password', '') or '')
        mqtt_transport = str(getattr(self, 'mqtt_transport', 'tcp') or 'tcp').strip().lower()
        mqtt_use_tls = _to_bool(getattr(self, 'mqtt_use_tls', False))
        mqtt_tls_insecure = _to_bool(getattr(self, 'mqtt_tls_insecure', False))
        mqtt_ws_path = str(getattr(self, 'mqtt_ws_path', '/mqtt') or '/mqtt').strip() or '/mqtt'
        if mqtt_transport not in {'tcp', 'websockets'}:
            mqtt_transport = 'tcp'
        
        # КРИТИЧНО: Используем clean_session=True для публичных MQTT брокеров
        client_kwargs = {"client_id": self.my_id, "clean_session": True, "transport": mqtt_transport}
        callback_api = getattr(mqtt, "CallbackAPIVersion", None)
        if callback_api is not None:
            version_attr = getattr(callback_api, "VERSION1", None) or getattr(callback_api, "V1", None)
            if version_attr is not None:
                client_kwargs["callback_api_version"] = version_attr
                
        try:
            self.client_mqqt = mqtt.Client(**client_kwargs)
            self.client_mqqt.on_connect = self.on_connect
            self.client_mqqt.on_disconnect = self.on_disconnect
            self.client_mqqt.on_message = self.on_message
            if mqtt_username:
                self.client_mqqt.username_pw_set(mqtt_username, mqtt_password or None)
            if mqtt_transport == 'websockets':
                self.client_mqqt.ws_set_options(path=mqtt_ws_path)
            if mqtt_use_tls:
                self.client_mqqt.tls_set()
                self.client_mqqt.tls_insecure_set(mqtt_tls_insecure)
            
            # Улучшенная обработка параметров подключения
            default_port = 1883
            if mqtt_use_tls:
                default_port = 443 if mqtt_transport == 'websockets' else 8883
            elif mqtt_transport == 'websockets':
                default_port = 8080
            mqtt_port = int(self.mqtt_port) if self.mqtt_port and str(self.mqtt_port).strip() else default_port
            mqtt_timeout = int(self.mqtt_timeout) if self.mqtt_timeout and str(self.mqtt_timeout).strip() else 60
            
            print(
                f'Connecting to MQTT broker: {self.mqtt_address}:{mqtt_port} '
                f'(transport={mqtt_transport}, tls={mqtt_use_tls})'
            )
            self.client_mqqt.connect(self.mqtt_address, mqtt_port, mqtt_timeout)
            self.client_mqqt.loop_start()
            
            # ТОПИКИ С ПРЕФИКСАМИ ДЛЯ ИЗОЛЯЦИИ СЕРВЕРОВ
            topics = [
                'server/status',
                'server/quit',
                'server/size',
                'server/update/first',
                'server/update/next',
                'server/keyboard/keypress',
                'server/keyboard/keyrelease',
                'server/mouse/position',
                'server/mouse/label',
                'server/mouse/right_click',
                'server/mouse/left_click',
                'server/mouse/double_click',
                'server/mouse/wheel',
                'server/mouse/drag_start',
                'server/mouse/move',
                'server/mouse/drag_end'
            ]
            print(f"\n=== SERVER SUBSCRIPTIONS С ПРЕФИКСАМИ ===")
            print(f"Topic prefix: '{self.topic_prefix}'")
            for topic in topics:
                full_topic = self.build_topic(topic)
                result = self.client_mqqt.subscribe(full_topic)
                print(f"Subscribed to: '{full_topic}' -> {result}")
            print(f"=== END SUBSCRIPTIONS ===\n")
                
            self.server_status = 'wait'
            self.publish_server_status()
            self.timer.start(1000)  # ОРИГИНАЛЬНЫЙ ТАЙМЕР 1000мс
            self.connect_mqtt = True
            print(f'Server started successfully with prefix: {self.topic_prefix}')
            
        except Exception as e:
            self.connect_mqtt = False
            print(f'Could not connect to the MQTT server: {e}')

    def has_active_clients(self):
        """Проверяем наличие активных подключенных клиентов"""
        active_count = sum(1 for info in self.clients.values() 
                          if info.get('status') == 'Connected')
        return active_count > 0
        
    def has_viewer_clients(self):
        """Проверяем наличие viewer-клиентов"""
        viewer_count = sum(1 for info in self.clients.values() 
                          if info.get('status') == 'Connected' and info.get('role') == 'viewer')
        return viewer_count > 0
        
    def get_client_stats(self):
        """Получаем статистику клиентов"""
        total = len(self.clients)
        active = sum(1 for info in self.clients.values() if info.get('status') == 'Connected')
        controller_name = self.clients.get(self.controller_id, {}).get('name', 'None') if self.controller_id else 'None'
        viewers = active - (1 if self.controller_id and self.controller_id in self.clients else 0)
        
        return {
            'total': total,
            'active': active,
            'controller': controller_name,
            'viewers': viewers
        }
        
    def send_mouse_position_update(self):
        """Отправляем позицию мыши только если есть активные клиенты"""
        if not self.client_mqqt or not self.has_active_clients():
            return
            
        try:
            x, y = self.mouse.position
            cursor_type = get_current_cursor()
            if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(cursor_type, str):
                self.client_mqqt.publish(
                    self.build_topic('client/mouse/position'), 
                    f"{x}|{y}|{cursor_type}|continuous"
                )
        except Exception as e:
            print(f"Error sending mouse position: {e}")

    def update_screen(self):
        if not self.connect_mqtt:  # No MQTT connection yet
            return
        if self.quit:  # Client ended the session; stay connected and reset state
            if self.client_mqqt:
                self.client_mqqt.publish(self.build_topic('client/quit'))
            self.reset_session_state()
            return
            
        # КРИТИЧЕСКИ ВАЖНО: Проверяем наличие активных клиентов
        if not self.has_active_clients():
            # Если нет активных клиентов, не отправляем события мыши/клавиатуры
            return
            
        # Only publish status occasionally, not every frame
        if not hasattr(self, '_status_counter'):
            self._status_counter = 0
        self._status_counter += 1
        if self._status_counter % 30 == 0:  # Every 30 frames (~4.5 seconds at 150ms)
            self.publish_server_status()
            
            # Логируем статистику клиентов каждые 30 фреймов
            stats = self.get_client_stats()
            if stats['active'] > 0:
                print(f"📊 STATS: Active={stats['active']}, Controller={stats['controller']}, Viewers={stats['viewers']}")
            
        # ОТПРАВЛЯЕМ ПОЗИЦИЮ МЫШИ ТОЛЬКО ЕСЛИ ЕСТЬ АКТИВНЫЕ КЛИЕНТЫ
        self.send_mouse_position_update()
