import cv2
from PyQt6 import QtCore
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap, QImage, QCursor
from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QSizePolicy
import paho.mqtt.client as mqtt
import time
import uuid
import zlib
import base64
import pickle
import socket
import queue

from cursor import MouseCursor
from pynput import keyboard

HOTPATH_LOGS = False


def _hotpath_log(message):
    if HOTPATH_LOGS:
        print(message)


class ScreenShareClient(QMainWindow):
    def __init__(self):
        super().__init__()

        # ОПРЕДЕЛЕНИЯ ДЛЯ ИЗОБРАЖЕНИЯ С СЕРВЕРА ___________________________________________________________________________
        self.screen_width, self.screen_height = 0, 0  # Размер экрана сервера пока не известен
        self.ask_size = False  # Показывает известен ли размер изображения с сервера
        self.capture = False  # Признак вывода предыдущего изображение, пока не выведено новое не запрашиваем
        self.quit, self.screen_size, self.first = False, False, False  # Признак выхода, размер картинки с сервера, признак первого кадра
        self.first_image = True  # Признак первого изображения в передаче экранов
        self.last_image = None  # Предыдущее изображение
        self.pixmap_resized = None  # Подгоняет размер пришедшего изображения под размер окна вывода
        self.last_next = ""  # Содержимое поля говорит о том рисовать курсор сервера last или клиента next (пока не видно реализации!!!!!!!!!)

        # ОПРЕДЕЛЕНИЯ ДЛЯ МЫШИ ________________________________________________________________________________________
        self.mouse_x, self.mouse_y = 0, 0  # Позиция курсора мыши на сервере
        self.orig_mouse_x, self.orig_mouse_y, self.orig_mouse_x_last, self.orig_mouse_y_last = -1, -1, -1, -1  # Предполагаемая позицыя мыши на сервере
        self.mouse_cursor = MouseCursor()
        self.cursor_type = ""

        # ИНТЕРФЕЙС _________________________________________________________________________________________________
        # Создайте QLabel для отображения изображения
        self.label = QLabel(self)
        # Разрешите масштабирование содержимого QLabel
        self.label.setScaledContents(True)
        # Prevent large pixmaps from forcing a large minimum window size after fullscreen.
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.label.setMinimumSize(1, 1)
        # Сделайте курсор мыши невидимым, когда он находится над self.label
        # self.label.setCursor(Qt.CursorShape.BlankCursor)
        self.label.setMouseTracking(True)  # но чтобы его могло отслеживать событие mouseMoveEvent

        # Создайте кнопку для запуска демонстрации экрана сервера
        self.start_button = QPushButton('Start Screen Share', self)
        self.start_button.clicked.connect(self.toggle_stream)
        self.fullscreen_button = QPushButton('Fullscreen', self)
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen_mode)

        # Установите макет для размещения виджетов
        self.status_label = QLabel('Status: Idle', self)
        self.role_label = QLabel('Role: Viewer', self)
        status_bar = self.statusBar()
        self.status_label.setContentsMargins(8, 0, 8, 0)
        self.role_label.setContentsMargins(8, 0, 8, 0)
        if status_bar is not None:
            status_bar.addWidget(self.status_label, 1)
            status_bar.addPermanentWidget(self.role_label)
        self.set_status_message('Disconnected')

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.fullscreen_button)
        controls_layout.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(controls_layout)
        layout.addWidget(self.label)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        # _________________________________________________________________________________КОНЕЦ ОПРЕДЕЛЕНИЯ ИНТЕРФЕЙСА

        # КРИТИЧНО: Создайте QTimer в конструкторе в главном потоке
        self.timer = QTimer(self)  # Передаем родительский объект
        self.timer.timeout.connect(self.update_screen)

        self.my_id = None
        self.client_name = socket.gethostname() or 'Client'
        self.role = 'viewer'
        self.is_controller = False
        self.client_mqqt = None
        self.connect_mqqt = False  # Нет подключения к серверу mqqt
        self.is_running = False
        self.server_status = 'wait'  # Статус сервера важен когда кто из слушателей будет ведущим для запроса экранов для всех
        self.pending_reconnect = False
        self.connection_stable = False  # Flag to prevent premature disconnection
        self.user_initiated_close = False  # Flag to track user-initiated close events
        self.role_assignment_pending = False
        self._is_stopping = False
        self._last_frame_request_at = 0.0
        self._frame_request_timeout_sec = 2.5
        self._last_size_request_at = 0.0
        self._size_request_retry_sec = 2.0
        # И важен, когда статус управления установлен. Статусы - wait - ожидает подключения, send есть главный слушатель, control - управляется
        self.server_address, self.server_password, self.mqtt_address, self.mqtt_port, self.mqtt_timeout = '', '', '', 0, 0
        self.mqtt_username = ''
        self.mqtt_password = ''
        self.mqtt_transport = 'tcp'
        self.mqtt_use_tls = False
        self.mqtt_tls_insecure = False
        self.mqtt_ws_path = '/mqtt'
        self.topic_prefix = ''
        self.viewer_window = None

        # ОПРЕДЕЛЕНИЯ ДЛЯ КЛАВИАТУРЫ __________________________________________________________________________________
        self.start_pos = 0  # Начальная позиция мыши для процедуры выделения
        self.mouse_is_pressed = False  # Признак нажатия левой кнопки мыши для начала процедуры выделения
        self.mouse_drag_with_shift = False  # Модификатор Shift для удаленного клика/перетаскивания
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Включаем получение событий клавиатуры

        self.listener = None
        # Start the keyboard controller
        self.controller = keyboard.Controller()
        self.current_keys = []
        self.special_keys = {
            '\\x01': 'a', '\\x02': 'b', '\\x03': 'c', '\\x04': 'd', '\\x05': 'e',
            '\\x06': 'f', '\\x07': 'g', '\\x08': 'h', '\\x09': 'i', '\\x0a': 'j',
            '\\x0b': 'k', '\\x0c': 'l', '\\x0d': 'm', '\\x0e': 'n', '\\x0f': 'o',
            '\\x10': 'p', '\\x11': 'q', '\\x12': 'r', '\\x13': 's', '\\x14': 't',
            '\\x15': 'u', '\\x16': 'v', '\\x17': 'w', '\\x18': 'x', '\\x19': 'y',
            '\\x1a': 'z', '<96>': '0', '<110>': '.', '<97>': '1', '<98>': '2',
            '<99>': '3', '<100>': '4', '<101>': '5', '<102>': '6', '<103>': '7',
            '<104>': '8', '<105>': '9', '+': 'plus', '<107>': 'plus',
        }
        self._ensure_keyboard_listener()
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

    def _run_on_ui_delayed(self, delay_ms, callback):
        self._run_on_ui(lambda: QtCore.QTimer.singleShot(delay_ms, callback))

    def reset_stream_state(self, clear_view=True):
        self.screen_width, self.screen_height = 0, 0
        self.ask_size = False
        self.capture = False
        self.quit = False
        self.screen_size = False
        self.first = False
        self.first_image = True
        self.last_image = None
        self.pixmap_resized = None
        self.last_next = ''
        self.mouse_x, self.mouse_y = 0, 0
        self.orig_mouse_x = -1
        self.orig_mouse_y = -1
        self.orig_mouse_x_last = -1
        self.orig_mouse_y_last = -1
        self.cursor_type = ''
        self.server_status = 'wait'
        self.set_role('viewer', update_status=False)
        self.set_status_message('Disconnected')
        self.start_pos = 0
        self.mouse_is_pressed = False
        self.mouse_drag_with_shift = False
        self.topic_prefix = ''
        self.client_mqqt = None
        self.connect_mqqt = False
        self.my_id = None
        self.pending_reconnect = False
        self.connection_stable = False
        self.role_assignment_pending = False
        self._last_frame_request_at = 0.0
        self._last_size_request_at = 0.0
        
        # ПОЛНАЯ ОЧИСТКА клавиатуры и модификаторов
        if hasattr(self, 'current_keys'):
            self.current_keys.clear()
            
        # Сбрасываем все модификаторы клавиатуры
        if hasattr(self, 'ctrl_pressed'):
            self.ctrl_pressed = False
        if hasattr(self, 'alt_pressed'):
            self.alt_pressed = False
        if hasattr(self, 'shift_pressed'):
            self.shift_pressed = False
            
        print("Stream state fully reset with keyboard/mouse cleanup")
        
        if clear_view and hasattr(self, 'label'):
            self.label.clear()


    def set_role(self, role, update_status=True):
        previous_is_controller = self.is_controller
        normalized = 'controller' if role == 'controller' else 'viewer'
        self.role = normalized
        self.is_controller = normalized == 'controller'
        if update_status:
            if self.is_controller:
                self.server_status = 'control'
            elif self.server_status != 'wait':
                self.server_status = 'view'
        if not self.is_controller and hasattr(self, 'current_keys'):
            self.current_keys.clear()
        if update_status:
            if self.is_controller:
                self.set_status_message('Controller')
                # Start screen sharing only on role transition.
                if not previous_is_controller:
                    self.initiate_screen_sharing()
            elif self.server_status == 'wait':
                self.set_status_message('Waiting for control')
            else:
                self.set_status_message('Viewing')
        self.update_role_label()
        
    def initiate_screen_sharing(self):
        """Start screen sharing process when client becomes controller"""
        print(f">>> INITIATING SCREEN SHARING <<<")
        print(f"MQTT client exists: {self.client_mqqt is not None}")
        print(f"connect_mqqt flag: {self.connect_mqqt}")
        print(f"Current screen_size: {self.screen_size}, screen dimensions: {self.screen_width}x{self.screen_height}")
        print(f"Timer active: {self.timer.isActive()}")
        
        if not self.client_mqqt:
            print("Cannot initiate screen sharing - no MQTT client")
            return
            
        # НЕ сбрасываем размер экрана если он уже известен!
        if not self.screen_size:
            print("Requesting screen size...")
            # Сбрасываем состояние ТОЛЬКО если размер неизвестен
            self.screen_width = 0
            self.screen_height = 0
            self.first = False
            self.ask_size = False
            
            # Запрашиваем размер экрана с сервера
            if not self._request_screen_size(force=True):
                return
        else:
            print(f"Screen size already known: {self.screen_width}x{self.screen_height}")
        
        # Всегда сбрасываем состояние кадров для нового потока
        self.first_image = True
        self.first = False  # КРИТИЧНО: сбрасываем флаг первого кадра
        self.capture = False
        self._last_frame_request_at = 0.0
        self.last_image = None
        print(f"[DEBUG] Reset frame state - first_image: {self.first_image}, first: {self.first}")
        
        # КРИТИЧНО: Если размер экрана уже известен И таймер не запущен, запускаем его!
        if self.screen_size and not self.timer.isActive() and self.connect_mqqt:
            print("[DEBUG] ✅ Starting timer NOW - screen size known and controller assigned!")
            # Используем QMetaObject.invokeMethod для безопасного запуска из любого потока
            from PyQt6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self.timer, "start",
                                   Qt.ConnectionType.QueuedConnection,
                                   QtCore.Q_ARG(int, 40))
        else:
            print(f"[DEBUG] Timer will start later - screen_size: {self.screen_size}, timer_active: {self.timer.isActive()}, connect_mqqt: {self.connect_mqqt}")

    def update_role_label(self):
        if hasattr(self, 'role_label') and self.role_label is not None:
            role_text = 'Controller' if self.is_controller else 'Viewer'
            self.role_label.setText(f"Role: {role_text}")

    def attempt_reconnect(self):
        """Попытка переподключения к MQTT брокеру"""
        if not self.is_running or self.connect_mqqt or self.pending_reconnect:
            print(f"Skipping reconnect - is_running: {self.is_running}, connect_mqqt: {self.connect_mqqt}, pending: {self.pending_reconnect}")
            return
            
        print("Attempting to reconnect to MQTT broker...")
        self.set_status_message('Reconnecting...')
        
        # Полная очистка перед переподключением
        if self.client_mqqt:
            try:
                self.client_mqqt.on_connect = None
                self.client_mqqt.on_disconnect = None
                self.client_mqqt.on_message = None
                self.client_mqqt.loop_stop()
                self.client_mqqt.disconnect()
            except Exception:
                pass
            self.client_mqqt = None
            
        self.connect_mqqt = False
        self.pending_reconnect = True
        
        try:
            self.run()
        except Exception as e:
            print(f"Reconnection failed: {e}")
            self.set_status_message(f'Reconnection failed: {e}')
            self.pending_reconnect = False
            
            # Повторная попытка через 10 секунд
            if self.is_running:
                self._run_on_ui_delayed(10000, self.attempt_reconnect)

    def set_status_message(self, message):
        if hasattr(self, 'status_label') and self.status_label is not None:
            self.status_label.setText(f"Status: {message}")

    def announce_disconnect(self):
        if self.client_mqqt and self.connect_mqqt:
            try:
                self.client_mqqt.publish(self.build_topic('server/quit'), self.my_id)
            except Exception:
                pass

    def _publish(self, topic, *args, **kwargs):
        if self.client_mqqt and self.connect_mqqt:
            self.client_mqqt.publish(topic, *args, **kwargs)

    def _can_send_remote_input(self, require_pointer=False):
        if not self.is_controller:
            return False
        if not self.client_mqqt or not self.connect_mqqt:
            return False
        if require_pointer:
            return self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0
        return True

    def _ensure_keyboard_listener(self):
        listener = getattr(self, 'listener', None)
        try:
            if listener is not None and getattr(listener, 'running', False):
                return
        except Exception:
            pass
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.listener.start()
        print("Keyboard listener started")

    def _publish_registration(self, client=None, reason=''):
        mqtt_client = client or self.client_mqqt
        if mqtt_client is None or not self.my_id:
            return False
        topic = self.build_topic('server/status')
        message = f"register|{self.my_id}|{self.client_name}"
        if reason:
            print(f"Registering with server ({reason}): {topic} -> {message}")
        else:
            print(f"Registering with server: {topic} -> {message}")
        try:
            mqtt_client.publish(topic, message)
            return True
        except Exception as exc:
            print(f"Registration publish failed: {exc}")
            return False

    def _schedule_registration_retry(self, client, delay_ms=2000, retries_left=2):
        if retries_left <= 0:
            return

        def retry():
            if not self.is_running or self._is_stopping:
                return
            if not self._is_current_mqtt_client(client):
                return
            if not self.connect_mqqt:
                return
            if not self.role_assignment_pending:
                return
            self._publish_registration(client=client, reason=f"retry x{retries_left}")
            self._schedule_registration_retry(client, delay_ms=delay_ms, retries_left=retries_left - 1)

        self._run_on_ui_delayed(delay_ms, retry)

    def _is_current_mqtt_client(self, client):
        return client is not None and client is self.client_mqqt

    def _request_screen_size(self, client=None, force=False):
        mqtt_client = client or self.client_mqqt
        if mqtt_client is None:
            return False
        now = time.time()
        if not force and now - self._last_size_request_at < self._size_request_retry_sec:
            return False
        try:
            result = mqtt_client.publish(self.build_topic('server/size'), "1", 0, True)
            self._last_size_request_at = now
            self.ask_size = True
            print(f"Screen size request sent - result: {result}")
            return True
        except Exception as exc:
            print(f"Error sending screen size request: {exc}")
            return False

    def build_topic(self, suffix: str) -> str:
        if self.topic_prefix:
            return f"{self.topic_prefix}/{suffix}"
        return suffix

    def toggle_stream(self):
        if self.is_running:
            self.stop_stream()
        else:
            self.start_stream()

    def set_viewer_window(self, viewer_window):
        self.viewer_window = viewer_window

    def on_viewer_fullscreen_changed(self, is_fullscreen):
        if hasattr(self, 'fullscreen_button') and self.fullscreen_button is not None:
            self.fullscreen_button.setText('Exit Fullscreen' if is_fullscreen else 'Fullscreen')
        if hasattr(self, 'start_button') and self.start_button is not None:
            self.start_button.setVisible(not is_fullscreen)
        if hasattr(self, 'fullscreen_button') and self.fullscreen_button is not None:
            self.fullscreen_button.setVisible(not is_fullscreen)
        status_bar = self.statusBar() if callable(getattr(self, 'statusBar', None)) else None
        if status_bar is not None:
            status_bar.setVisible(not is_fullscreen)

    def _resolve_viewer_window(self):
        # Preferred explicit binding from server-side viewer host.
        window = getattr(self, 'viewer_window', None)
        if window is not None and callable(getattr(window, 'toggle_fullscreen_mode', None)):
            return window

        # Fallback: walk parent chain to find a host window that supports fullscreen toggle.
        parent = self.parentWidget()
        while parent is not None:
            if callable(getattr(parent, 'toggle_fullscreen_mode', None)):
                return parent
            parent = parent.parentWidget()
        return None

    def toggle_fullscreen_mode(self):
        # Preferred path for viewer mode hosted by the server-side viewer window.
        window = self._resolve_viewer_window()
        toggle = getattr(window, 'toggle_fullscreen_mode', None)
        if callable(toggle):
            toggle()
            is_full = False
            state_getter = getattr(window, 'is_fullscreen_mode', None)
            if callable(state_getter):
                is_full = bool(state_getter())
            elif hasattr(window, 'isFullScreen'):
                is_full = bool(window.isFullScreen())
            self.on_viewer_fullscreen_changed(is_full)
            return

        # Hard fallback: toggle top-level window directly.
        host_window = self.window() if callable(getattr(self, 'window', None)) else None
        if host_window is None:
            host_window = self
        if hasattr(host_window, 'isFullScreen') and hasattr(host_window, 'showFullScreen') and hasattr(host_window, 'showNormal'):
            if host_window.isFullScreen():
                host_window.showNormal()
                self.on_viewer_fullscreen_changed(False)
            else:
                host_window.showFullScreen()
                self.on_viewer_fullscreen_changed(True)

    def start_stream(self):
        if self.is_running:
            return
        print(f"Starting stream - server_address: {self.server_address}, mqtt_address: {self.mqtt_address}")
        self._is_stopping = False
        self.pending_reconnect = False
        self.reset_stream_state()
        self._ensure_keyboard_listener()
        self.is_running = True
        self.set_status_message('Connecting...')
        self.start_button.setText('Stop Screen Share')
        self.my_id = str(uuid.uuid4()) + str(time.time())
        print('Client Id = ' + self.my_id)
        try:
            self.run()
        except Exception as exc:
            print(f"Error starting stream: {exc}")
            import traceback
            traceback.print_exc()
            self.stop_stream()

    def stop_stream(self):
        """Полная очистка ресурсов при отключении клиента"""
        print(f"stop_stream called - is_running: {self.is_running}, connect_mqqt: {self.connect_mqqt}")
        
        if not self.is_running and not self.connect_mqqt:
            print("Already stopped, ignoring stop_stream call")
            return

        self._is_stopping = True
        self.pending_reconnect = False
        self.is_running = False
            
        # Уведомляем сервер об отключении
        self.announce_disconnect()
        
        # Останавливаем все таймеры
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            print("Timer stopped")
            
        # Полная очистка MQTT соединения
        self.disconnect_from_server()
        
        # Останавливаем слушатель клавиатуры
        if hasattr(self, 'listener') and self.listener is not None:
            try:
                if hasattr(self.listener, 'running') and self.listener.running:
                    self.listener.stop()
                    print("Keyboard listener stopped")
                self.listener = None
            except Exception as e:
                print(f"Error stopping keyboard listener: {e}")
        
        # Сбрасываем все состояния
        self.reset_stream_state()
        self._is_stopping = False
        self.start_button.setText('Start Screen Share')
        self.set_status_message('Disconnected')
        print("Client fully stopped")
        
    def user_close(self):
        """Called when user explicitly closes the client"""
        print("User-initiated close")
        self.user_initiated_close = True
        self.stop_stream()

    def disconnect_from_server(self):
        """Полное отключение от MQTT сервера"""
        print(f"disconnect_from_server called - connect_mqqt: {self.connect_mqqt}, client exists: {self.client_mqqt is not None}")
        
        if self.client_mqqt:
            try:
                self.client_mqqt.on_connect = None
                self.client_mqqt.on_disconnect = None
                self.client_mqqt.on_message = None
                print("Stopping MQTT loop")
                self.client_mqqt.loop_stop()
            except Exception as e:
                print(f"Error stopping MQTT loop: {e}")
            
            try:
                print("Disconnecting from MQTT broker")
                self.client_mqqt.disconnect()
            except Exception as e:
                print(f"Error disconnecting from MQTT: {e}")
                
            # Очищаем ссылку на клиента
            self.client_mqqt = None
            
        self.connect_mqqt = False
        self.topic_prefix = ''
        print("MQTT client fully disconnected and cleaned")

    def closeEvent(self, a0):
        """Обработчик закрытия окна клиента - ПОЛНАЯ ОЧИСТКА"""
        print(f"Client window closeEvent called - is_running: {self.is_running}")
        
        # ПОЛНАЯ ОЧИСТКА ПРИ ЗАКРЫТИИ ОКНА
        self.user_initiated_close = True
        
        # Останавливаем поток данных если он активен
        if self.is_running:
            print("Stopping stream due to window close")
            self.stop_stream()
        
        # Останавливаем слушатель клавиатуры с проверками на None
        if hasattr(self, 'listener') and self.listener is not None:
            try:
                if hasattr(self.listener, 'running') and self.listener.running:
                    print("Stopping keyboard listener on window close")
                    self.listener.stop()
                self.listener = None
            except Exception as e:
                print(f"Error stopping keyboard listener: {e}")
        
        # Очищаем список нажатых клавиш
        if hasattr(self, 'current_keys'):
            self.current_keys.clear()
            
        # ПОЛНАЯ ОЧИСТКА всех состояний мыши и клавиатуры
        self.orig_mouse_x = -1
        self.orig_mouse_y = -1
        self.orig_mouse_x_last = -1
        self.orig_mouse_y_last = -1
        self.mouse_is_pressed = False
        
        # Очищаем модификаторы клавиатуры 
        if hasattr(self, 'ctrl_pressed'):
            self.ctrl_pressed = False
        if hasattr(self, 'alt_pressed'):
            self.alt_pressed = False
        if hasattr(self, 'shift_pressed'):
            self.shift_pressed = False
            
        # Сбрасываем состояние курсора
        if hasattr(self, 'cursor_type'):
            self.cursor_type = 'default'
        
        print("Client window cleanup completed")
        super().closeEvent(a0)

    def resizeEvent(self, a0):
        """Обработчик изменения размера окна для обновления отображения"""
        super().resizeEvent(a0)
        # Если есть изображение для отображения, обновляем его масштабирование
        if self.last_image is not None and hasattr(self, 'pixmap_resized') and self.pixmap_resized is not None:
            # Заново масштабируем изображение под новый размер окна
            height, width, channel = self.last_image.shape
            bytes_per_line = 3 * width
            image_bgr = cv2.cvtColor(self.last_image, cv2.COLOR_BGR2RGB)
            image_with_cursor = self.mouse_cursor.draw(image_bgr, self.mouse_x, self.mouse_y, self.cursor_type)
            qImg = QImage(image_with_cursor.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            
            label_width = max(self.label.width(), 1)
            label_height = max(self.label.height(), 1)
            
            self.pixmap_resized = qImg.scaled(label_width, label_height,
                                              QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                              QtCore.Qt.TransformationMode.SmoothTransformation)
            self.label.setPixmap(QPixmap.fromImage(self.pixmap_resized))

    def get_key_name(self, key):
        key_name = str(key).replace('Key.', '').lower().strip("'")
        for special_key, replacement in self.special_keys.items():
            if special_key in key_name:
                key_name = key_name.replace(special_key, replacement)
        return key_name

    def on_press(self, key):
        # КРИТИКО: Только CONTROLLER может отправлять события клавиатуры!
        if not self.is_controller:
            return
            
        if self._can_send_remote_input():
            key_name = self.get_key_name(key)
            if key_name not in self.current_keys:
                self.current_keys.append(key_name)
                key_sequence = '+'.join(self.current_keys)
                print(f'[CONTROLLER] Нажата клавиша: {key_sequence}')
                if self.client_mqqt:
                    self.client_mqqt.publish(self.build_topic('server/keyboard/keypress'), key_sequence)
                print("key_name", key_name)
                if 'alt_l' in self.current_keys and 'shift' in self.current_keys:
                    if self.listener is not None:
                        try:
                            if hasattr(self.listener, 'running') and self.listener.running:
                                self.listener.stop()
                        except Exception as e:
                            print(f"Error stopping listener: {e}")
                    self.listener = None
                    self.controller = keyboard.Controller()
                    self.listener = keyboard.Listener(
                        on_press=self.on_press,
                        on_release=self.on_release)
                    self.listener.start()
                if key_name not in ['ctrl_l', 'ctrl_r', 'alt_l', 'alt_l', 'shift', 'shift_r']:
                    self.on_release(key)

    def on_release(self, key):
        key_name = self.get_key_name(key)
        if key_name in self.current_keys:
            self.current_keys.remove(key_name)

    def mousePressEvent(self, a0):
        # КРИТИКО: Только CONTROLLER может отправлять события мыши!
        if not self.is_controller:
            super().mousePressEvent(a0)
            return
            
        if a0 is not None and self._can_send_remote_input(require_pointer=True):
            if a0.button() == Qt.MouseButton.RightButton:
                if self.client_mqqt:
                    self.client_mqqt.publish(self.build_topic('server/mouse/right_click'), f"({self.orig_mouse_x}, {self.orig_mouse_y})")
            elif a0.button() == Qt.MouseButton.LeftButton:
                self.mouse_is_pressed = True
                self.start_pos = QtCore.QPointF(self.orig_mouse_x, self.orig_mouse_y)
                self.mouse_drag_with_shift = bool(a0.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                if self.client_mqqt:
                    left_click_payload = f"({self.orig_mouse_x}, {self.orig_mouse_y})"
                    if self.mouse_drag_with_shift:
                        left_click_payload = f"{left_click_payload}|shift"
                    self.client_mqqt.publish(self.build_topic('server/mouse/drag_start'))
                    self.client_mqqt.publish(self.build_topic('server/mouse/left_click'), left_click_payload)
        super().mousePressEvent(a0)

    def mouseReleaseEvent(self, a0):
        # КРИТИКО: Только CONTROLLER может отправлять события мыши!
        if not self.is_controller:
            super().mouseReleaseEvent(a0)
            return
            
        if a0 is not None and a0.button() == Qt.MouseButton.LeftButton:
            self.mouse_is_pressed = False
            if self.client_mqqt and self.connect_mqqt:
                self.client_mqqt.publish(self.build_topic('server/mouse/drag_end'))
            self.mouse_drag_with_shift = False
        super().mouseReleaseEvent(a0)

    def mouseMoveEvent(self, a0):
        if not self.is_controller:
            super().mouseMoveEvent(a0)
            return
        if self._can_send_remote_input():
            self.mouse_label()
        super().mouseMoveEvent(a0)

    # def mouseDoubleClickEvent(self, event):
    #     if self.isActiveWindow() and self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
    #         # print(f'Двойной клик мыши в позиции ({event.position().x()}, {event.position().y()})')
    #         self._publish(self.build_topic('server/mouse/double_click'), f"({self.orig_mouse_x}, {self.orig_mouse_y})")
    #     super().mouseDoubleClickEvent(event)

    def wheelEvent(self, a0):
        # КРИТИКО: Только CONTROLLER может отправлять события мыши!
        if not self.is_controller:
            super().wheelEvent(a0)
            return
            
        if a0 is not None and self._can_send_remote_input(require_pointer=True):
            degrees = a0.angleDelta().y() / 8  # Преобразуем в градусы
            steps = degrees / 15  # Преобразуем в шаги
            if self.client_mqqt:
                self.client_mqqt.publish(self.build_topic('server/mouse/wheel'), f"{steps} steps")
        super().wheelEvent(a0)

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if not self._is_current_mqtt_client(client):
            print("Ignoring on_connect from stale MQTT client")
            return
        print('Connected flags ' + str(flags) + ' ,result code=' + str(rc))
        if self._is_stopping or not self.is_running:
            print("Ignoring on_connect because stream is stopping")
            return
        if rc == 0:
            try:
                print(f'Successfully connected to MQTT broker')
                print(f'Topic prefix: {self.topic_prefix}')
                self.role_assignment_pending = True
                
                # ИСПОЛЬЗУЕМ ОРИГИНАЛЬНУЮ ЛОГИКУ ПОДПИСКИ ИЗ util/client_20231123.py
                client.subscribe(self.build_topic('client/status'))
                client.subscribe(self.build_topic('client/size'))
                client.subscribe(self.build_topic('client/update/first'))
                client.subscribe(self.build_topic('client/update/next'))
                client.subscribe(self.build_topic('client/stream/first'))
                client.subscribe(self.build_topic('client/stream/next'))
                client.subscribe(self.build_topic('client/mouse/position'))
                client.subscribe(self.build_topic('client/quit'))
                print(f'Subscribed to all client topics')
                
                # Register with server + safe retries until role is assigned.
                self._publish_registration(client=client, reason='initial')
                self._schedule_registration_retry(client, delay_ms=2000, retries_left=3)
                
                # Запросим размер экрана - как в оригинальном коде
                if not self.screen_size:
                    self._request_screen_size(client=client, force=True)
                
                def handle():
                    self.connect_mqqt = True
                    self.pending_reconnect = False
                    self.connection_stable = True
                    self.set_status_message('Connected')
                    
                    # Используем QTimer.singleShot для запуска таймера в главном потоке
                    def try_start_timer():
                        if self.screen_size and not self.timer.isActive():
                            print('Starting update timer in main thread - screen size is known')
                            self.timer.start(40)
                        else:
                            print(f'Timer not started - screen_size: {self.screen_size}, timer_active: {self.timer.isActive()}')
                    
                    self._run_on_ui_delayed(100, try_start_timer)  # Небольшая задержка для получения размера
                self._run_on_ui(handle)
                
            except Exception as e:
                print(f"Error during connect setup: {e}")
                import traceback
                traceback.print_exc()
                self._run_on_ui(lambda: self.set_status_message(f"Connect setup error: {e}"))
        else:
            error_msg = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }.get(rc, f"Connection refused - code {rc}")
            print(f'Connection failed: {error_msg}')
            self.pending_reconnect = False
            self._run_on_ui(lambda: self.set_status_message(error_msg))
            if self.is_running and not self._is_stopping:
                self._run_on_ui_delayed(2000, self.attempt_reconnect)

    def on_disconnect(self, client, userdata, rc, properties=None):
        """Обработчик отключения от MQTT брокера"""
        if not self._is_current_mqtt_client(client):
            print("Ignoring on_disconnect from stale MQTT client")
            return
        print(f"MQTT disconnection event - code: {rc}, was_connected: {self.connect_mqqt}, is_running: {self.is_running}")
        
        def handle():
            was_connected = self.connect_mqqt
            self.connect_mqqt = False
            self.pending_reconnect = False
            self.role_assignment_pending = False
            
            if rc == 0:
                # Нормальное отключение по инициативе клиента
                print("Clean disconnection from MQTT broker")
                self.set_status_message('Disconnected')
            elif rc != 0 and self.is_running and was_connected and not self._is_stopping:
                # Неожиданное отключение
                print(f"Unexpected disconnection from MQTT broker, code: {rc}")
                self.set_status_message('Connection lost')
                if hasattr(self, 'timer'):
                    self.timer.stop()
                # Попытка переподключения через 5 секунд
                self._run_on_ui_delayed(5000, self.attempt_reconnect)
            else:
                print(f"Disconnection - was_connected: {was_connected}, is_running: {self.is_running}")
                self.set_status_message('Disconnected')
                
        self._run_on_ui(handle)

    def on_message(self, client, userdata, message):
        """Обработка сообщений с префиксами топиков"""
        if not self._is_current_mqtt_client(client):
            return
        topic = message.topic
        _hotpath_log(f"Client received message on topic: {topic}")
        
        # ОБРАБОТКА С ПРЕФИКСАМИ - КОМБИНИРУЕМ ОРИГИНАЛЬНУЮ ЛОГИКУ С ПРЕФИКСАМИ
        
        # Обработка статуса сервера
        if topic == self.build_topic('client/status'):
            payload = message.payload.decode('utf-8')
            print(f"[DEBUG] Received client/status message: {payload}")
            
            if payload.startswith('status|'):
                parts = payload.split('|', 1)
                if len(parts) > 1:
                    status_value = parts[1]
                    if status_value == 'control' and not self.is_controller:
                        self.server_status = 'view'
                    else:
                        self.server_status = status_value or 'view'
                    status_map = {
                        'wait': 'Waiting for control',
                        'control': 'Controller',
                        'view': 'Viewing'
                    }
                    display_status = status_map.get(self.server_status, self.server_status.title())
                    self.set_status_message(display_status)
                    print(f"[DEBUG] Server status updated to: {self.server_status}")
                return
                
            if payload.startswith('role|'):
                parts = payload.split('|', 2)
                print(f"[DEBUG] Role message parts: {parts}")
                if len(parts) > 2:
                    client_id = parts[1]
                    role = parts[2]
                    print(f"[DEBUG] Checking role assignment - my_id: '{self.my_id}', received_id: '{client_id}', role: '{role}'")
                    if client_id == self.my_id:
                        self.role_assignment_pending = False
                        print(f"[DEBUG] ✅ ROLE MATCH! Setting my role to: {role}")
                        self.set_role(role)
                    else:
                        print(f"[DEBUG] ❌ ROLE MISMATCH - not for me")
                return
                
            if payload.startswith('command|'):
                parts = payload.split('|', 3)
                if len(parts) > 2:
                    client_id = parts[1]
                    command = parts[2]
                    if client_id == self.my_id and command == 'disconnect':
                        print(f"Received disconnect command")
                        self.stop_stream()
                return
        
        if topic == self.build_topic('client/size'):
            if self.screen_width == 0 and self.screen_height == 0:
                strsize = message.payload.decode("utf-8")
                strlist = strsize.split("|")
                self.screen_width = int(strlist[0])
                self.screen_height = int(strlist[1])
                self.screen_size = True
                self.ask_size = False
                print(f"Got screen size: {self.screen_width}x{self.screen_height}")
                
                # КРИТИЧНО: Используем QMetaObject.invokeMethod для запуска в главном потоке
                def start_timer_in_main_thread():
                    print(f"[DEBUG] Timer check - connect_mqqt: {self.connect_mqqt}, timer_active: {self.timer.isActive()}, is_controller: {self.is_controller}")
                    if not self.timer.isActive() and self.connect_mqqt:
                        print("[DEBUG] Starting timer from screen size handler...")
                        from PyQt6.QtCore import QMetaObject, Qt
                        QMetaObject.invokeMethod(self.timer, "start",
                                               Qt.ConnectionType.QueuedConnection,
                                               QtCore.Q_ARG(int, 40))
                        print("Timer start requested in main thread after receiving screen size")
                        
                        # Если мы Controller, запускаем процесс запроса кадров
                        if self.is_controller:
                            print("Controller ready - will start requesting frames")
                    else:
                        print(f"[DEBUG] Timer NOT started - reasons: timer_active={self.timer.isActive()}, connect_mqqt={self.connect_mqqt}")
                
                self._run_on_ui(start_timer_in_main_thread)

        if topic == self.build_topic('client/mouse/position'):
            str_mouse_position = message.payload.decode("utf-8")
            str_list = str_mouse_position.split("|")
            self.mouse_x = int(str_list[0])
            self.mouse_y = int(str_list[1])
            self.cursor_type = str_list[2]
            if len(str_list) > 3:
                self.last_next = str_list[3]

        # Обработка кадров для CONTROLLER (прямые обновления)
        if topic == self.build_topic('client/update/first'):
            _hotpath_log("[CONTROLLER] Received direct first frame")
            if self.screen_size:
                _hotpath_log("[DEBUG] Processing first frame for controller")
                self.DecodeAndShowPayload(message, False)
                self.first = True
            else:
                _hotpath_log("[DEBUG] Skipping first frame - screen size not known")

        if topic == self.build_topic('client/update/next'):
            _hotpath_log("[CONTROLLER] Received direct next frame")
            if self.screen_size and self.first:
                _hotpath_log("[DEBUG] Processing next frame for controller")
                self.DecodeAndShowPayload(message)
            else:
                _hotpath_log(f"[DEBUG] Skipping next frame - screen_size: {self.screen_size}, first: {self.first}")
                
        # Обработка кадров для VIEWER (потоковые обновления)
        if topic == self.build_topic('client/stream/first'):
            _hotpath_log("[VIEWER] Received stream first frame")
            if self.screen_size:
                _hotpath_log("[DEBUG] Processing first frame for viewer")
                self.DecodeAndShowPayload(message, False)
                self.first = True
            else:
                _hotpath_log("[DEBUG] Skipping first frame - screen size not known")

        if topic == self.build_topic('client/stream/next'):
            _hotpath_log("[VIEWER] Received stream next frame")
            if self.screen_size and self.first:
                _hotpath_log("[DEBUG] Processing next frame for viewer")
                self.DecodeAndShowPayload(message)
            else:
                _hotpath_log(f"[DEBUG] Skipping next frame - screen_size: {self.screen_size}, first: {self.first}")

        if topic == self.build_topic('client/quit'):
            print("Received quit message")
            self.quit = True

    def _handle_message(self, topic, raw_payload):
        """ИНТЕГРИРОВАННЫЙ обработчик сообщений на основе util/client_20231123.py"""
        try:
            _hotpath_log(f"Client received message on topic: {topic}")
            
            # Создаем объект сообщения как в оригинальном коде
            from types import SimpleNamespace
            message = SimpleNamespace(topic=topic, payload=raw_payload)
            
            # ИСПОЛЬЗУЕМ ОРИГИНАЛЬНУЮ ЛОГИКУ ИЗ util/client_20231123.py
            
            if message.topic == self.build_topic('client/status'):
                payload = message.payload.decode('utf-8')
                if payload.startswith('status|'):
                    parts = payload.split('|', 1)
                    if len(parts) > 1:
                        status_value = parts[1]
                        if status_value == 'control' and not self.is_controller:
                            self.server_status = 'view'
                        else:
                            self.server_status = status_value or 'view'
                        status_map = {
                            'wait': 'Waiting for control',
                            'control': 'Controller',
                            'view': 'Viewing'
                        }
                        display_status = status_map.get(self.server_status, self.server_status.title())
                        self.set_status_message(display_status)
                    return
                if payload.startswith('role|'):
                    parts = payload.split('|', 2)
                    if len(parts) > 2:
                        client_id = parts[1]
                        role = parts[2]
                        if client_id == self.my_id:
                            print(f"Setting my role to: {role}")
                            self.set_role(role)
                    return
                if payload.startswith('command|'):
                    parts = payload.split('|', 3)
                    if len(parts) > 2:
                        client_id = parts[1]
                        command = parts[2]
                        if client_id == self.my_id and command == 'disconnect':
                            print(f"Received disconnect command")
                            self.stop_stream()
                    return
                if payload == 'wait':
                    self.server_status = 'wait'
                    self.set_status_message('Waiting for control')
                    self.set_role('viewer', update_status=False)
                    return
                if payload == 'control':
                    self.set_role('controller')
                    return

            if message.topic == self.build_topic('client/size'):
                if self.screen_width == 0 and self.screen_height == 0:
                    strsize = message.payload.decode("utf-8")
                    strlist = strsize.split("|")
                    self.screen_width = int(strlist[0])
                    self.screen_height = int(strlist[1])
                    self.screen_size = True
                    print(f"Screen size set to: {self.screen_width}x{self.screen_height}")

            if message.topic == self.build_topic('client/mouse/position'):
                str_mouse_position = message.payload.decode("utf-8")
                str_list = str_mouse_position.split("|")
                self.mouse_x = int(str_list[0])
                self.mouse_y = int(str_list[1])
                self.cursor_type = str_list[2]
                if len(str_list) > 3:
                    self.last_next = str_list[3]

            # Остальные обработчики исключены - используем обработчики из on_message
            
            if message.topic == self.build_topic('client/quit'):
                print("Received quit message")
                self.quit = True
                
        except Exception as e:
            print(f"Error in client _handle_message: {e}")
            import traceback
            traceback.print_exc()

    def DecodeAndShowPayload(self, message, next_frame=True):
        try:
            _hotpath_log(f"[DEBUG] DecodeAndShowPayload called - next_frame: {next_frame}")
            if next_frame:
                xor_image = pickle.loads(zlib.decompress(base64.b64decode(message.payload), 15, 65535))
                image = self.last_image ^ xor_image
            else:
                image = pickle.loads(zlib.decompress(base64.b64decode(message.payload), 15, 65535))
            self.last_image = image
            _hotpath_log(f"[DEBUG] Frame decoded successfully - image shape: {image.shape}")
            self.mouse_label()

            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            image = self.mouse_cursor.draw(image, self.mouse_x, self.mouse_y,
                                     self.cursor_type)  # Добавляем курсор мыши на изображение

            # Преобразуйте изображение в формат, который может быть отображен QLabel
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            qImg = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

            # Масштабирование с сохранением пропорций и высоким качеством
            label_width = max(self.label.width(), 1)
            label_height = max(self.label.height(), 1)
            
            self.pixmap_resized = qImg.scaled(label_width, label_height,
                                              QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                              QtCore.Qt.TransformationMode.SmoothTransformation)
            self.label.setPixmap(QPixmap.fromImage(self.pixmap_resized))
            _hotpath_log(f"[DEBUG] Frame displayed successfully - scaled to {label_width}x{label_height}")
            
            # Обновляем флаг capture для следующего запроса
            self.capture = False
            self._last_frame_request_at = 0.0
            
        except Exception as e:
            print(f"Error in DecodeAndShowPayload: {e}")
            import traceback
            traceback.print_exc()
            self.capture = False
            self._last_frame_request_at = 0.0

    def mouse_label(self):
        """Обновленный метод с префиксами топиков"""
        if self.first_image and not self.capture:
            return
        if self.last_image is None:
            return
        # Получите текущие координаты курсора мыши
        mouse_x, mouse_y = self.label.mapFromGlobal(QCursor.pos()).x(), self.label.mapFromGlobal(QCursor.pos()).y()

        # Проверьте, находится ли курсор мыши внутри self.label
        if mouse_x < 0 or mouse_y < 0 or mouse_x > self.label.width() or mouse_y > self.label.height():
            self.orig_mouse_x, self.orig_mouse_y = -1, -1
        else:
            # Вычислите соотношение масштабирования
            scale_ratio_w = self.last_image.shape[1] / self.label.width()
            scale_ratio_h = self.last_image.shape[0] / self.label.height()

            # Получите координаты курсора на исходном изображении
            self.orig_mouse_x = round(mouse_x * scale_ratio_w)
            self.orig_mouse_y = round(mouse_y * scale_ratio_h)
            if not self.orig_mouse_x == self.orig_mouse_x_last or not self.orig_mouse_y == self.orig_mouse_y_last:
                if self.client_mqqt:
                    self.client_mqqt.publish(self.build_topic('server/mouse/move'))
                self.orig_mouse_x_last = self.orig_mouse_x
                self.orig_mouse_y_last = self.orig_mouse_y
        if self._can_send_remote_input(require_pointer=True):
            if self.client_mqqt:
                self.client_mqqt.publish(self.build_topic('server/mouse/label'), str(self.orig_mouse_x) + "|" + str(self.orig_mouse_y))

    def run(self):
        """ИСПРАВЛЕННЫЙ МЕТОД С ПОДДЕРЖКОЙ ПРЕФИКСОВ ТОПИКОВ"""
        if not self.is_running:
            return
        if self.connect_mqqt:
            return
            
        address = (self.server_address or '').strip()
        password = (self.server_password or '').strip()
        
        if not address:
            self.set_status_message('No server address configured')
            return
            
        if not self.mqtt_address:
            self.set_status_message('No MQTT broker configured')
            return
            
        # СОЗДАЕМ ПРЕФИКС ТОПИКА ИЗ АДРЕСА И ПАРОЛЯ СЕРВЕРА
        self.topic_prefix = f"{address}/{password}"
        print(f"Client using topic prefix: {self.topic_prefix}")

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
        try:
            # LWT помогает серверу корректно снять зависший клиент при аварийном разрыве.
            self.client_mqqt.will_set(
                self.build_topic('server/status'),
                f"disconnect|{self.my_id}",
                qos=1,
                retain=False,
            )
        except Exception as exc:
            print(f"Could not configure LWT: {exc}")
        
        try:
            # Подключение к MQTT брокеру
            default_port = 1883
            if mqtt_use_tls:
                default_port = 443 if mqtt_transport == 'websockets' else 8883
            elif mqtt_transport == 'websockets':
                default_port = 8080
            mqtt_port = int(self.mqtt_port) if self.mqtt_port and str(self.mqtt_port).strip() else default_port
            mqtt_timeout = int(self.mqtt_timeout) if self.mqtt_timeout and str(self.mqtt_timeout).strip() else 60
            print(
                f"Connecting to MQTT broker: {self.mqtt_address}:{mqtt_port} "
                f"(transport={mqtt_transport}, tls={mqtt_use_tls})"
            )
            self.client_mqqt.connect(self.mqtt_address, mqtt_port, mqtt_timeout)
            self.client_mqqt.loop_start()

            print("Connection setup completed")
            self.set_status_message('Connecting...')
            
        except Exception as exc:
            print(f'Could not connect to the MQTT server: {exc}')
            self.set_status_message(f'Connection error: {exc}')
            self.stop_stream()

    def update_screen(self):
        """Обновленный метод с разделением Controller vs Viewer"""
        _hotpath_log(f"[UPDATE_SCREEN] Called - quit: {self.quit}, capture: {self.capture}, is_controller: {self.is_controller}")
        
        if self.quit:
            _hotpath_log("[UPDATE_SCREEN] Quitting - stopping timer")
            self.timer.stop()
            if self.client_mqqt:
                self.client_mqqt.loop_stop()
                self.client_mqqt.disconnect()
            return

        if self.capture:
            now = time.time()
            if self._last_frame_request_at and (now - self._last_frame_request_at) > self._frame_request_timeout_sec:
                print(f"[WARN] Frame request timeout ({now - self._last_frame_request_at:.2f}s) - recovering stream state")
                self.capture = False
                self.first_image = True
            else:
                _hotpath_log("[DEBUG] Skipping frame request - capture flag is True")
                return

        if not self.screen_size:
            if self.connect_mqqt:
                self._request_screen_size()
            _hotpath_log("[DEBUG] Skipping frame request - screen size unknown")
            return

        # КРИТИЧНО: ТОЛЬКО CONTROLLER может запрашивать кадры у сервера!
        if not self.is_controller:
            # Viewer-клиенты НЕ запрашивают кадры, а получают их через подписку
            _hotpath_log("[DEBUG] Not controller - not requesting frames")
            return

        _hotpath_log(f"[CONTROLLER DEBUG] Requesting frame - first_image: {self.first_image}, capture: {self.capture}")
        self.capture = True
        self._last_frame_request_at = time.time()
        
        if self.first_image:
            if self.client_mqqt:
                result = self.client_mqqt.publish(self.build_topic('server/update/first'))
                _hotpath_log(f"[CONTROLLER] Requested first frame - result: {result}")
            self.first_image = False
        else:
            if self.client_mqqt:
                result = self.client_mqqt.publish(self.build_topic('server/update/next'))
                _hotpath_log(f"[CONTROLLER] Requested next frame - result: {result}")
