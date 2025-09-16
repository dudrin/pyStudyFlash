import time
import socket
import os
from PyQt6 import QtCore, QtGui, QtWidgets
import random
import cv2
import pyautogui
import numpy as np
from pynput import mouse, keyboard


class RecoverThread(QtCore.QThread):
    frame_changed = QtCore.pyqtSignal(object)

    def __init__(self):
        QtCore.QThread.__init__(self)

    def recv_msg(self):
        try:
            msg_length = self.client_socket.recv(64).decode()
        except ConnectionResetError:
            print("Соединение было прервано")
            return
        except OSError:
            print("Сокет не подключен")
            return

        if msg_length:
            msg_length = int(msg_length)
            msg = self.client_socket.recv(msg_length).decode()
            return msg

    def recv_file(self, file_name):
        msg = self.recv_msg()
        if msg is None:
            print("Соединение было прервано")
            return
        counter_position = int(msg)
        with open(file_name, "wb") as f:
            try:
                bytes_recv = self.client_socket.recv(1024)
            except ConnectionResetError:
                print("Соединение было прервано")
                return
            counter = 0
            while True:
                counter += 1
                f.write(bytes_recv)
                if counter == counter_position:
                    break
                bytes_recv = self.client_socket.recv(1024)

    def run(self):
        while True:
            self.client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            try:
                self.client_socket.connect((ui.HOST_RECVER, ui.PORT_RECVER))
            except ConnectionRefusedError:
                print("Не удалось подключиться к серверу")
            rand_int = random.randint(1000, 9999)
            self.recv_file(f"frame_Client_Recver_{rand_int}.jpg")
            pixmap = QtGui.QPixmap(f"frame_Client_Recver_{rand_int}.jpg")
            ui.pixmap_resized = pixmap.scaled(ui.label.width(), ui.label.height(),
                                              QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            self.frame_changed.emit('%s' % (f"frame_Client_Recver_{rand_int}.jpg"))
            time.sleep(0.01)


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
            self.client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            try:
                self.client_socket.connect((ui.HOST_SENDER, ui.PORT_SENDER))
            except ConnectionRefusedError:
                print("Не удалось подключиться к серверу")
            image = pyautogui.screenshot()
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            rand_int = random.randint(1000, 9999)
            cv2.imwrite(f"frame_Client_Sender_{rand_int}.jpg", image)
            try:
                self.send_file(f"frame_Client_Sender_{rand_int}.jpg")
            except:
                pass
            os.remove(f"frame_Client_Sender_{rand_int}.jpg")
            time.sleep(0.01)


class EventSenderThread(QtCore.QThread):
    def __init__(self, window):
        QtCore.QThread.__init__(self)
        self.window = window
        self.mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click
        )
        self.mouse_listener.start()
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press
        )
        self.keyboard_listener.start()

    def run(self):
        self.event_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.event_socket.connect((ui.HOST_SENDER, 12498))  # Используйте тот же порт

    def on_move(self, x, y):
        if hasattr(self, 'event_socket'):
            if self.window.isActiveWindow() and self.window.geometry().contains(QtGui.QCursor.pos()):
                msg = f'mouse_move {x} {y}'
                message = msg.encode()
                msg_length = len(message)
                send_length = str(msg_length).encode()
                send_length += b" " * (64 - len(send_length))
                try:
                    self.event_socket.send(send_length)
                    self.event_socket.send(message)
                    # Передаем информацию о видимости курсора мыши
                    cursor_visible = QtGui.QCursor().shape() != QtCore.Qt.CursorShape.BlankCursor
                    msg = f'cursor_visible {cursor_visible}'
                    message = msg.encode()
                    msg_length = len(message)
                    send_length = str(msg_length).encode()
                    send_length += b" " * (64 - len(send_length))
                    self.event_socket.send(send_length)
                    self.event_socket.send(message)
                except OSError:
                    print("Сокет не подключен")

    def on_click(self, x, y, button, pressed):
        if self.window.isActiveWindow() and self.window.geometry().contains(QtGui.QCursor.pos()):
            if pressed:
                msg = f'mouse_click {button.name}'
                message = msg.encode()
                msg_length = len(message)
                send_length = str(msg_length).encode()
                send_length += b" " * (64 - len(send_length))
                try:
                    self.event_socket.send(send_length)
                    self.event_socket.send(message)
                except OSError:
                    print("Сокет не подключен")

    def on_press(self, key):
        if self.window.isActiveWindow() and self.window.geometry().contains(QtGui.QCursor.pos()):
            msg = f'key_press {key}'
            message = msg.encode()
            msg_length = len(message)
            send_length = str(msg_length).encode()
            send_length += b" " * (64 - len(send_length))
            try:
                self.event_socket.send(send_length)
                self.event_socket.send(message)
            except OSError:
                print("Сокет не подключен")


class UiForm(QtWidgets.QWidget):

    def __init__(self, host_recover, port_recover, host_sender, port_sender):
        super().__init__()
        self.setObjectName("Form")
        self.resize(800, 400)
        self.setMinimumSize(800, 400)
        self.setWindowTitle("RECEIVING VIDEO")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self)
        self.label.setText("")
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.HOST_RECVER = host_recover
        self.PORT_RECVER = port_recover

        self.HOST_SENDER = host_sender
        self.PORT_SENDER = port_sender

    def show_frame(self, data):
        self.label.setPixmap(self.pixmap_resized)
        os.remove(data)

    def send_frame(self):
        pass

    def start_recver(self):
        self.recver = RecoverThread()
        self.recver.frame_changed.connect(self.show_frame)
        self.recver.start()

    def start_sender(self):
        self.sender = SenderThread()
        self.sender.frame_changed.connect(self.send_frame)
        self.sender.start()

    def start_event_sender(self, window):
        self.event_sender = EventSenderThread(window)
        self.event_sender.start()

    def close_event(self, event):
        print("[CLIENT] stopped")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    ui = UiForm("::1", 54537, "::1", 54536)  #::1
    ui.show()
    ui.start_recver()
    ui.start_sender()
    ui.start_event_sender(ui)  # Запускаем поток отправки событий
    sys.exit(app.exec())
