import sys

import cv2
from PyQt6 import QtCore
from PyQt6.QtCore import QTimer, Qt, QEvent
from PyQt6.QtGui import QPixmap, QImage, QCursor, QKeySequence, QKeyEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QGraphicsView, \
    QGraphicsScene, QGraphicsPixmapItem
import paho.mqtt.client as mqtt
import time
import uuid
from mss.tools import zlib
import base64
import pickle
from cursor import MouseCursor


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

        # Создайте QGraphicsView для отображения изображения
        self.graphicsView = QGraphicsView()
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.graphicsView.installEventFilter(self)
        # Создайте QGraphicsScene в конструкторе
        self.scene = QGraphicsScene()
        # Создайте QGraphicsPixmapItem в конструкторе и добавьте его на сцену
        self.pixmapItem = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmapItem)
        # Установите QGraphicsScene для вашего QGraphicsView
        self.graphicsView.setScene(self.scene)

        # Создайте кнопку для запуска демонстрации экрана сервера
        self.start_button = QPushButton('Start Screen Share', self)
        self.start_button.clicked.connect(self.run)

        # Установите макет для размещения виджетов
        layout = QVBoxLayout()
        layout.addWidget(self.start_button)
        layout.addWidget(self.graphicsView)

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

    def eventFilter(self, obj, event):
        print(event.type())
        if event.type() == QEvent.Type.KeyPress:
            print("Сработало")
            keyEvent = QKeyEvent(event)
            if self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
                modifiers = []
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    modifiers.append('ctrl')
                if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                    modifiers.append('alt')
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    modifiers.append('shift')
                key = QKeySequence(event.key()).toString().lower()
                if keyEvent.key() == Qt.Key.Key_Tab:
                    key = 'tab'
                key_sequence = '+'.join(modifiers + [key])
                print(f'Нажата клавиша: {key_sequence}')
                self.client_mqqt.publish("server/keyboard/keypress", key_sequence)
        return QMainWindow.eventFilter(self, obj, event)

    # def keyPressEvent(self, event):
    #     if self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
    #         modifiers = []
    #         if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
    #             modifiers.append('ctrl')
    #         if event.modifiers() & Qt.KeyboardModifier.AltModifier:
    #             modifiers.append('alt')
    #         if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
    #             modifiers.append('shift')
    #         key = QKeySequence(event.key()).toString().lower()
    #         key_sequence = '+'.join(modifiers + [key])
    #         print(f'Нажата клавиша: {key_sequence}')
    #         self.client_mqqt.publish("server/keyboard/keypress", key_sequence)

    # def keyReleaseEvent(self, event):
    #     if self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
    #         key_sequence = QKeySequence(event.modifiers() | event.key()).toString()
    #         print(f'Отпущена клавиша: {key_sequence}')
    #         self.client_mqqt.publish("server/keyboard/keyrelease", key_sequence)

    def mousePressEvent(self, event):
        if self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
            if event.button() == Qt.MouseButton.RightButton:
                self.client_mqqt.publish("server/mouse/right_click", f"({self.orig_mouse_x}, {self.orig_mouse_y})")
            elif event.button() == Qt.MouseButton.LeftButton:
                self.mouse_is_pressed = True
                self.start_pos = QtCore.QPointF(self.orig_mouse_x, self.orig_mouse_y)
                self.client_mqqt.publish("server/mouse/drag_start")
                self.client_mqqt.publish("server/mouse/left_click", f"({self.orig_mouse_x}, {self.orig_mouse_y})")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
            if event.button() == Qt.MouseButton.LeftButton:
                self.mouse_is_pressed = False
                self.client_mqqt.publish("server/mouse/drag_end")
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
            # print(f'Двойной клик мыши в позиции ({event.position().x()}, {event.position().y()})')
            self.client_mqqt.publish("server/mouse/double_click", f"({self.orig_mouse_x}, {self.orig_mouse_y})")
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if self.orig_mouse_x >= 0 and self.orig_mouse_y >= 0:
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
            # if self.last_next == 'last':
            #     self.orig_mouse_x_last = self.orig_mouse_x
            #     self.orig_mouse_y_last = self.orig_mouse_y
            #     # Вычислите соотношение масштабирования
            #     scale_ratio_w = self.last_image.shape[1] / self.label.width()
            #     scale_ratio_h = self.last_image.shape[0] / self.label.height()
            #
            #     # Получите координаты курсора на исходном изображении
            #     mouse_x = round(self.mouse_x / scale_ratio_w)
            #     mouse_y = round(self.mouse_y / scale_ratio_h)
            #     global_pos = self.label.mapToGlobal(QtCore.QPoint(mouse_x, mouse_y))
            #     QCursor.setPos(global_pos)

        if message.topic == "client/update/first":
            if self.size:
                self.DecodeAndShowPayload(message, False)
                self.first = True

        if message.topic == "client/update/next":
            if self.size and self.first:
                self.DecodeAndShowPayload(message)

        if message.topic == "client/quit":
            self.quit = True

    def DecodeAndShowPayload(self, message, NextFrame=True):
        # if self.last_next == 'next':
        self.mouse_label()
        if NextFrame:
            xor_image = pickle.loads(zlib.decompress(base64.b64decode(message.payload), 15, 65535))
            image = self.last_image ^ xor_image
        else:
            image = pickle.loads(zlib.decompress(base64.b64decode(message.payload), 15, 65535))
        self.last_image = image

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        image = self.cursor.draw(image, self.mouse_x, self.mouse_y,
                                 self.cursor_type)  # Добавляем курсор мыши на изображение

        # Преобразуйте изображение в формат, который может быть отображен QLabel
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        qImg = QImage(image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

        # Масштабируйте QImage
        qImg_resized = qImg.scaled(self.graphicsView.width(), self.graphicsView.height(),
                                   Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)

        # Создайте QPixmap из масштабированного QImage
        pixmap = QPixmap.fromImage(qImg)

        # Обновите QPixmap у вашего QGraphicsPixmapItem
        self.pixmapItem.setPixmap(pixmap)

        # QCoreApplication.processEvents()

        # Обновите QGraphicsView
        # self.graphicsView.update()
        # self.graphicsView.repaint()

        # Масштабируйте изображение, чтобы оно соответствовало размеру вашего QGraphicsView
        self.graphicsView.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.capture = False

    def mouse_label(self):
        # Получите текущие координаты курсора мыши относительно self.graphicsView
        mouse_x, mouse_y = self.graphicsView.mapFromGlobal(QCursor.pos()).x(), self.graphicsView.mapFromGlobal(
            QCursor.pos()).y()

        # Проверьте, находится ли курсор мыши внутри self.graphicsView
        if mouse_x < 0 or mouse_y < 0 or mouse_x > self.graphicsView.width() or mouse_y > self.graphicsView.height():
            self.orig_mouse_x, self.orig_mouse_y = -1, -1
        else:
            # Вычислите соотношение масштабирования
            scale_ratio_w = self.last_image.shape[1] / self.graphicsView.width()
            scale_ratio_h = self.last_image.shape[0] / self.graphicsView.height()

            # Получите координаты курсора на исходном изображении
            self.orig_mouse_x = round(mouse_x * scale_ratio_w)
            self.orig_mouse_y = round(mouse_y * scale_ratio_h)
            if not self.orig_mouse_x == self.orig_mouse_x_last or not self.orig_mouse_y == self.orig_mouse_y_last:
                self.client_mqqt.publish("server/mouse/move")
                self.orig_mouse_x_last = self.orig_mouse_x
                self.orig_mouse_y_last = self.orig_mouse_y
        self.client_mqqt.publish("server/mouse/label", str(self.orig_mouse_x) + "|" + str(self.orig_mouse_y))
        # self.client_mqqt.publish("server/mouse/position")

    def run(self):
        self.client_mqqt = mqtt.Client(self.my_id, False)
        self.client_mqqt.on_connect = self.on_connect
        self.client_mqqt.on_message = self.on_message
        try:
            self.client_mqqt.connect("10.1.1.66")
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = ScreenShareClient()
    client.show()
    sys.exit(app.exec())
