import socket
import os
from PyQt6 import QtCore, QtGui, QtWidgets
import random
import cv2
import pyautogui
import numpy as np
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController


class RecverThread(QtCore.QThread):
    frame_changed = QtCore.pyqtSignal(object)

    def __init__(self):
        QtCore.QThread.__init__(self)
        # self.mouse = MouseController()
        # self.keyboard = KeyboardController()

    def recv_msg(self):
        msg_length = self.client_socket.recv(64).decode()
        if msg_length:
            msg_length = int(msg_length)
            msg = self.client_socket.recv(msg_length).decode()
            return msg

    def recv_file(self, file_name):
        counter_position = int(self.recv_msg())
        with open(file_name, "wb") as f:
            bytes_recv = self.client_socket.recv(1024)
            counter = 0
            while True:
                counter += 1
                f.write(bytes_recv)
                if counter == counter_position:
                    break
                bytes_recv = self.client_socket.recv(1024)

    def run(self):
        while True:
            self.server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.server_socket.bind((ui.HOST_RECVER, ui.PORT_RECVER))
            self.server_socket.listen(5)
            self.client_socket, self.addr = self.server_socket.accept()
            rand_int = random.randint(1000, 9999)
            self.recv_file(f"frame_Server_Recver_{rand_int}.jpg")
            pixmap = QtGui.QPixmap(f"frame_Server_Recver_{rand_int}.jpg")
            ui.pixmap_resized = pixmap.scaled(ui.label.width(), ui.label.height(),
                                              QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            self.frame_changed.emit('%s' % (f"frame_Server_Recver_{rand_int}.jpg"))
            data = self.recv_msg()


class SenderThread(QtCore.QThread):
    frame_changed = QtCore.pyqtSignal(object)

    def __init__(self):
        QtCore.QThread.__init__(self)

    def send_file(self, filename):
        msg = str(-(-int(os.path.getsize(filename)) // 1024))
        message = msg.encode()
        msg_length = len(message)
        send_length = str(msg_length).encode()
        send_length += b" " * (64 - len(send_length))
        self.client_socket.send(send_length)
        self.client_socket.send(message)
        counter = 0
        with open(filename, "rb") as f:
            while True:
                counter += 1
                file_bytes = f.read(1024)
                if not file_bytes:
                    break
                self.client_socket.sendall(file_bytes)

    def run(self):
        while True:
            self.server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.server_socket.bind((ui.HOST_SENDER, ui.PORT_SENDER))
            self.server_socket.listen(5)
            self.client_socket, self.addr = self.server_socket.accept()
            image = pyautogui.screenshot()
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            # Получите текущее положение курсора мыши
            x, y = pyautogui.position()
            # Нарисуйте центральную точку курсора мыши
            cv2.circle(image, (x, y), 1, (0, 0, 255), -1)
            # Нарисуйте верхнюю точку курсора мыши
            cv2.circle(image, (x, y - 3), 1, (0, 0, 255), -1)
            # Нарисуйте нижнюю точку курсора мыши
            cv2.circle(image, (x, y + 3), 1, (0, 0, 255), -1)

            # Нарисуйте левую точку курсора мыши
            cv2.circle(image, (x - 3, y), 1, (0, 0, 255), -1)

            # Нарисуйте правую точку курсора мыши
            cv2.circle(image, (x + 3, y), 1, (0, 0, 255), -1)

            rand_int = random.randint(1000, 9999)
            cv2.imwrite(f"frame_Server_Sender_{rand_int}.jpg", image)  # .png
            self.send_file(f"frame_Server_Sender_{rand_int}.jpg")
            os.remove(f"frame_Server_Sender_{rand_int}.jpg")


class EventThread(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)
        self.mouse = MouseController()
        self.keyboard = KeyboardController()

    def recv_msg(self):
        msg_length = self.client_socket.recv(64).decode()
        if msg_length:
            msg_length = int(msg_length)
            msg = self.client_socket.recv(msg_length).decode()
            return msg

    def run(self):
        self.event_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.event_socket.bind((ui.HOST_RECVER, 12498))  # Используйте другой порт
        self.event_socket.listen(5)
        self.client_socket, self.addr = self.event_socket.accept()

        while True:
            data = self.recv_msg()
            if data is not None:
                if data.startswith('mouse_move'):
                    x, y = map(int, data.split()[1:])
                    self.mouse.move(x, y)
                    print(x, y)
                elif data.startswith('mouse_click'):
                    button_name = data.split()[1]
                    button = getattr(Button, button_name)
                    self.mouse.click(button)
                elif data.startswith('key_press'):
                    key_name = data.split()[1]
                    key = getattr(Key, key_name)
                    self.keyboard.press(key)
                    self.keyboard.release(key)


class UiForm(QtWidgets.QWidget):
    def __init__(self, host_recver, port_recver, host_sender, port_sender):
        super().__init__()
        self.setObjectName("Form")
        self.resize(800, 400)
        self.setMinimumSize(800, 400)
        self.setWindowTitle("SENDING VIDEO")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self)
        self.label.setText("")
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.HOST_RECVER = host_recver
        self.PORT_RECVER = port_recver

        self.HOST_SENDER = host_sender
        self.PORT_SENDER = port_sender

    def show_frame(self, data):
        self.label.setPixmap(self.pixmap_resized)
        os.remove(data)

    def send_frame(self):
        pass

    def start_recver(self):
        self.recver = RecverThread()
        self.recver.frame_changed.connect(self.show_frame)
        self.recver.start()

    def start_sender(self):
        self.sender = SenderThread()
        self.sender.frame_changed.connect(self.send_frame)
        self.sender.start()

    def start_event_thread(self):
        self.event_thread = EventThread()
        self.event_thread.start()

    def closeEvent(self, event):
        print("[SERVER] stopped")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    ui = UiForm("::1", 54536, "::1", 54537)
    ui.show()
    ui.start_recver()
    ui.start_sender()
    ui.start_event_thread()  # Запускаем поток обработки событий
    sys.exit(app.exec())
