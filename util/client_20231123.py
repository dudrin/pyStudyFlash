import cv2
from PyQt6 import QtCore
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap, QImage, QCursor
from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QPushButton, QWidget
import paho.mqtt.client as mqtt
import time
import uuid
from mss.tools import zlib
import base64
import pickle

from cursor import MouseCursor
from pynput import keyboard


class ScreenShareClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.last_next = ""  # Содержимое поля говорит о том рисовать курсор сервера last или клиента next
        self.pixmap_resized = None
        self.quit, self.size, self.capture, self.first = False, False, False, False
        self.width, self.height = 0, 0  # Размер экрана сервера пока не известен
        self.last_image = None
        self.mouse_x, self.mouse_y = 0, 0  # Позиция курсора мыши на сервере
        self.orig_mouse_x, self.orig_mouse_y, self.orig_mouse_x_last, self.orig_mouse_y_last = -1, -1, -1, -1  # Предполагаемая позицыя мыши на сервере
        self.cursor = MouseCursor()
        self.cursor_type = ""
        self.first_image = True
        # Создайте QLabel для отображения изображения
        self.label = QLabel(self)
        # Разрешите масштабирование содержимого QLabel
        self.label.setScaledContents(True)
        # Сделайте курсор мыши невидимым, когда он находится над self.label
        # self.label.setCursor(Qt.CursorShape.BlankCursor)
        self.label.setMouseTracking(True)  # но чтобы его могло отслеживать событие mouseMoveEvent

        # Создайте кнопку для запуска демонстрации экрана сервера
        self.start_button = QPushButton('Start Screen Share', self)
        self.start_button.clicked.connect(self.run)

        # Установите макет для размещения виджетов
        layout = QVBoxLayout()
        layout.addWidget(self.start_button)
        layout.addWidget(self.label)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Создайте QTimer в конструкторе
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_screen)

        self.my_id = str(uuid.uuid4()) + str(time.time())
        print("Client Id = " + self.my_id)
        self.client_mqqt = ""
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Включаем получение событий клавиатуры

        self.start_pos = 0  # Начальная позиция мыши для процедуры выделения
        self.mouse_is_pressed = False  # Признак нажатия левой кнопки мыши для начала процедуры выделения

        # Start the keyboard listener
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.listener.start()
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
            '<104>': '8', '<105>': '9', '+': 'plus',
        }

    def get_key_name(self, key):
        key_name = str(key).replace('Key.', '').lower().strip("'")
        for special_key, replacement in self.special_keys.items():
            if special_key in key_name:
                key_name = key_name.replace(special_key, replacement)
        return key_name

    def on_press(self, key):
        if self.isActiveWindow() and self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
            key_name = self.get_key_name(key)
            if key_name not in self.current_keys:
                self.current_keys.append(key_name)
                key_sequence = '+'.join(self.current_keys)
                print(f'Нажата клавиша: {key_sequence}')
                self.client_mqqt.publish("server/keyboard/keypress", key_sequence)
                print("key_name", key_name)
                if 'alt_l' in self.current_keys and 'shift' in self.current_keys:
                    self.listener.stop()
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

    def mousePressEvent(self, event):
        if self.isActiveWindow() and self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
            if event.button() == Qt.MouseButton.RightButton:
                self.client_mqqt.publish("server/mouse/right_click", f"({self.orig_mouse_x}, {self.orig_mouse_y})")
            elif event.button() == Qt.MouseButton.LeftButton:
                self.mouse_is_pressed = True
                self.start_pos = QtCore.QPointF(self.orig_mouse_x, self.orig_mouse_y)
                self.client_mqqt.publish("server/mouse/drag_start")
                self.client_mqqt.publish("server/mouse/left_click", f"({self.orig_mouse_x}, {self.orig_mouse_y})")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isActiveWindow() and self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
            if event.button() == Qt.MouseButton.LeftButton:
                self.mouse_is_pressed = False
                self.client_mqqt.publish("server/mouse/drag_end")
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.isActiveWindow() and self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
            # print(f'Двойной клик мыши в позиции ({event.position().x()}, {event.position().y()})')
            self.client_mqqt.publish("server/mouse/double_click", f"({self.orig_mouse_x}, {self.orig_mouse_y})")
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if self.isActiveWindow() and self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
            degrees = event.angleDelta().y() / 8  # Преобразуем в градусы
            steps = degrees / 15  # Преобразуем в шаги
            # print(f'Вращение колесика мыши: {steps} шагов')
            self.client_mqqt.publish("server/mouse/wheel", f"{steps} steps")
        super().wheelEvent(event)

    def on_connect(self, client, userdata, flags, rc):
        print("Connected flags " + str(flags) + " ,result code=" + str(rc))

    def on_message(self, client, userdata, message):
        # print("Приходят сообщения с сервера!!!", message.topic)
        if message.topic == "client/size":
            if self.width == 0 and self.height == 0:
                strsize = message.payload.decode("utf-8")
                strlist = strsize.split("|")
                self.width = int(strlist[0])
                self.height = int(strlist[1])
                self.size = True

        if message.topic == "client/mouse/position":
            str_mouse_position = message.payload.decode("utf-8")
            str_list = str_mouse_position.split("|")
            self.mouse_x = int(str_list[0])
            self.mouse_y = int(str_list[1])
            self.cursor_type = str_list[2]
            self.last_next = str_list[3]

        if message.topic == "client/update/first":
            if self.size:
                self.DecodeAndShowPayload(message, False)
                self.first = True

        if message.topic == "client/update/next":
            if self.size and self.first:
                self.DecodeAndShowPayload(message)

        if message.topic == "client/quit":
            self.quit = True

    def DecodeAndShowPayload(self, message, next_frame=True):
        if next_frame:
            xor_image = pickle.loads(zlib.decompress(base64.b64decode(message.payload), 15, 65535))
            image = self.last_image ^ xor_image
        else:
            image = pickle.loads(zlib.decompress(base64.b64decode(message.payload), 15, 65535))
        self.last_image = image
        self.mouse_label()

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        image = self.cursor.draw(image, self.mouse_x, self.mouse_y,
                                 self.cursor_type)  # Добавляем курсор мыши на изображение

        # Преобразуйте изображение в формат, который может быть отображен QLabel
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        qImg = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

        # # Отобразите изображение с помощью QLabel
        self.pixmap_resized = qImg.scaled(self.label.width(), self.label.height(),
                                          QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                          QtCore.Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(QPixmap.fromImage(self.pixmap_resized))
        self.capture = False

    def mouse_label(self):
        if self.first_image and not self.capture:
            return
        # Получите текущие координаты курсора мыши относительно self.label
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
                self.client_mqqt.publish("server/mouse/move")
                self.orig_mouse_x_last = self.orig_mouse_x
                self.orig_mouse_y_last = self.orig_mouse_y
        if self.isActiveWindow() and self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
            self.client_mqqt.publish("server/mouse/label", str(self.orig_mouse_x) + "|" + str(self.orig_mouse_y))

    def run(self):
        self.client_mqqt = mqtt.Client(self.my_id, False)
        self.client_mqqt.on_connect = self.on_connect
        self.client_mqqt.on_message = self.on_message
        try:
            # self.client_mqqt.connect("10.1.1.66")
            self.client_mqqt.connect("broker.hivemq.com", 1883, 60)
            self.client_mqqt.loop_start()
            self.client_mqqt.subscribe("client/size")
            self.client_mqqt.subscribe("client/update/first")
            self.client_mqqt.subscribe("client/update/next")
            self.client_mqqt.subscribe("client/mouse/position")
            self.client_mqqt.subscribe("client/quit")

            ask_size = False
            while not self.size:
                if not ask_size:
                    self.client_mqqt.publish("server/size", "1", 0, True)
                    ask_size = True
                time.sleep(1)

            self.timer.start(40)  # Запустите таймер при запуске

        except:
            print("Could not connect to the Mosquito server")

    def update_screen(self):
        if self.quit:
            self.timer.stop()  # Остановите таймер, если self.quit истинно
            self.client_mqqt.loop_stop()
            self.client_mqqt.disconnect()
            return

        if self.capture:
            return

        self.capture = True
        if self.first_image:
            self.client_mqqt.publish("server/update/first")
            self.first_image = False
        else:
            self.client_mqqt.publish("server/update/next")


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     client = ScreenShareClient()
#     client.show()
#     sys.exit(app.exec())
