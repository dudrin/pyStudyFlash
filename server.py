import pyautogui
import pyperclip
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMainWindow
import paho.mqtt.client as mqtt
import time
import uuid
import mss
from mss.tools import zlib
import numpy
import base64
import pickle
# import pydirectinput
from pynput import mouse as mouse_move
from pynput.keyboard import Controller, Key
from pynput.mouse import Controller as MouseController
from classes.get_cursor import get_current_cursor
from classes.timer_server import MyTimer


class ScreenShareServer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mqtt_timeout = None
        self.mqtt_address = None
        self.mqtt_port = None
        self.server_password, self.server_address, self.mqtt_timeout, self.mqtt_address, self.mqtt_port = None, None, None, None, None
        self.connect_mqtt = False  # Признак подкличения к mqtt серверу
        self.monitor = 0  # all monitors
        self.quit, self.capture, self.last_image = False, False, None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_screen)

        self.listener = mouse_move.Listener(on_move=self.on_move)
        self.listener.start()
        self.mouse_move_on_server = False
        self.timer_block_mouse_client = MyTimer(5.0, self.on_timer)  # Создаем таймер на 5 секунд для блокировки клиента, т.к. на сервере используют мышь это больший приоритет

        self.keyboard = Controller()
        self.mouse = MouseController()

        self.setMouseTracking(True)

        self.mouse_label_x, self.mouse_label_y = -1, -1  # Выводим позицию курсора мыши за экран

        self.my_id = str(uuid.uuid4()) + str(time.time())
        print("Client Id = " + self.my_id)
        self.client_mqqt = ""

        self.mouse_released = False  # показывает, что левая кнопка мыши отжата
        self.mouse_move = False  # мышь на клиенте в движении

        self.server_status = "wait"  # wait - сервер ожидает соединения, send - раздает экран, control - управляется

    def on_move(self, x, y):  # Если на сервере начато перемещение мыши
        if not self.mouse_move:  # Если на клиенте не перемещается мышь
            # print('!', self.mouse_move)
            if not self.timer_block_mouse_client.isActive():  # Проверяем, работает ли таймер
                self.mouse_move_on_server = True  # Пока True клиент не сможет управлять мышью на сервере
                self.timer_block_mouse_client.start()
        self.mouse_move = False

    def on_timer(self):  # Сработал таймер - блокировка управления мышью на сервере для клиента снята
        # print('Сработал таймер', time.time())
        self.timer_block_mouse_client.stop()
        self.mouse_move_on_server = False  # Клиенту разрешено управлять мышью сервера

    def on_connect(self, client, userdata, flags, rc):  # Событие подключения к MQTT серверу
        print("Connected flags " + str(flags) + " ,result code=" + str(rc))
        self.connect_mqtt = True  # Есть подключение к MQTT серверу

    def on_disconnect(self, client, userdata, flags, rc):  # Событие отключения от MQTT сервера
        self.connect_mqtt = False
        print("Disconnected flags " + str(flags) + " ,result code=" + str(rc))

    def on_message(self, client, userdata, message):  # Подписываемся на события с клиента отправляемые на сервер
        if message.topic == "server/status" and message.payload.decode("utf-8") == "control":
            client.subscribe("server/size")
            client.subscribe("server/update/first")
            client.subscribe("server/update/next")
            client.subscribe("server/keyboard/keypress")
            client.subscribe("server/keyboard/keyrelease")
            client.subscribe("server/mouse/position")
            client.subscribe("server/mouse/label")
            client.subscribe("server/mouse/right_click")
            client.subscribe("server/mouse/left_click")
            client.subscribe("server/mouse/double_click")
            client.subscribe("server/mouse/wheel")
            client.subscribe("server/mouse/drag_start")
            client.subscribe("server/mouse/move")
            client.subscribe("server/mouse/drag_end")
            self.server_status = "control"
            print("Подписались!!!")

        if message.topic == "server/size":  # Определяем размер экрана
            with mss.mss() as sct:
                sct_img = sct.grab(sct.monitors[self.monitor])
                size = sct_img.size
                client.publish("client/size", str(size.width) + "|" + str(size.height))  # Посылаем размер на клиент

        if message.topic == "server/keyboard/keypress":  # обработка нажатий клавиш на клиенте
            key_sequence = message.payload.decode()
            print(message.topic + " " + str(key_sequence))
            keys = key_sequence.split('+')
            try:
                # Если ключ содержит более одного символа, это специальная клавиша
                if len(keys) == 1 and len(keys[0]) > 1 and not keys[0].lower() == 'plus':
                    if keys[0].lower() == 'plus':
                        keys[0] = '+'
                    self.keyboard.press(getattr(Key, keys[0]))
                    self.keyboard.release(getattr(Key, keys[0]))
                elif '+' in key_sequence:
                    if keys[1].lower() == 'plus':
                        keys[1] = '+'
                    # Если одним из ключей является 'shift' и есть только один другой ключ, который является буквой длиной 1, используем копирование и вставку
                    if 'shift' in keys and len(keys) == 2 and len(keys[1]) == 1 and keys[1].isalpha():
                        # pyperclip.copy(keys[1].upper())
                        # self.keyboard = Controller()
                        self.keyboard.press(keys[1].upper())
                        # self.keyboard.press(Key.ctrl)
                        # self.keyboard.press('v')
                        # self.keyboard.release('v')
                        # self.keyboard.release(Key.ctrl)
                    else:
                        # if 'shift' in keys and 'alt_l' in keys:
                        #    self.keyboard = Controller()
                        for key in keys:
                            print(key)
                            if not keys[1].lower() == 'ctrl_l':
                                if len(key) > 1:
                                    # print(getattr(Key, key))
                                    self.keyboard.press(getattr(Key, key))
                                else:
                                    self.keyboard.press(keys[1])
                        time.sleep(0.01)
                        for key in reversed(keys):
                            if not keys[1].lower() == 'ctrl_l':
                                if len(key) > 1:
                                    self.keyboard.release(getattr(Key, key))
                                else:
                                    self.keyboard.release(keys[1])
                else:
                    if keys[0].lower() == 'plus':
                        key_sequence = '+'
                    self.keyboard.press(key_sequence)
                    self.keyboard.release(key_sequence)
            except:
                print("Что-то не та клавиша(и) прошла(и)!")
            self.keyboard.release(Key.esc)
            self.keyboard.release(Key.ctrl)
            self.keyboard.release(Key.alt)
            self.keyboard.release(Key.shift)

        elif message.topic == "server/keyboard/keyrelease":
            pass  # Ничего не делаем при отпускании клавиши

        if message.topic == "server/mouse/right_click":
            x, y = map(int, message.payload.decode()[1:-1].split(', '))
            pyautogui.rightClick(x, y)
        elif message.topic == "server/mouse/left_click":
            x, y = map(int, message.payload.decode()[1:-1].split(', '))
            pyautogui.mouseDown(x, y)
        elif message.topic == "server/mouse/double_click":
            x, y = map(int, message.payload.decode()[1:-1].split(', '))
            print("DbClick")
            pyautogui.doubleClick(x, y)
        elif message.topic == "server/mouse/wheel":
            steps = int(float(message.payload.decode().split(' ')[0]))
            # print(steps)
            pyautogui.scroll(steps * 100)

        if message.topic == "server/mouse/drag_start":
            self.mouse_released = False
        elif message.topic == "server/mouse/drag_end":
            self.mouse_released = True
            pyautogui.mouseUp()

        if message.topic == "server/mouse/move":
            self.mouse_move = True

        if message.topic == "server/update/first":
            with mss.mss() as sct:
                b64img = self.BuildPayload(False)
                client.publish("client/update/first", b64img)

        if message.topic == "server/update/next":
            with mss.mss() as sct:
                b64img = self.BuildPayload()
                client.publish("client/update/next", b64img)

        if message.topic == "server/mouse/position":
            with mss.mss() as sct:
                # Получите текущее положение курсора мыши
                x, y = pyautogui.position()
                # Получаем текущий тип курсора
                cursor_type = get_current_cursor()
                if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(cursor_type, str):
                    client.publish("client/mouse/position", str(x) + "|" + str(y) + "|" + cursor_type)

        if message.topic == "server/mouse/label":  # Предполагаемые позиции мыши с клиента управления для отображения курсора
            str_mouse_position = message.payload.decode("utf-8")
            str_list = str_mouse_position.split("|")
            self.mouse_label_x = int(str_list[0])
            self.mouse_label_y = int(str_list[1])
            # print(self.mouse_label_x, '!', self.mouse_label_y, '!', 'self.mouse_move ', self.mouse_move, 'self.mouse_move_on_server ', self.mouse_move_on_server)
            if self.mouse_label_x >= 0 and self.mouse_label_y >= 0 and self.mouse_move and not self.mouse_move_on_server:
                # pyautogui.moveTo(self.mouse_label_x, self.mouse_label_y)
                self.mouse.position = (self.mouse_label_x, self.mouse_label_y)
                cursor_type = get_current_cursor()
                if isinstance(self.mouse_label_x, (int, float)) and isinstance(self.mouse_label_y,
                                                                               (int, float)) and isinstance(cursor_type,
                                                                                                            str):
                    client.publish("client/mouse/position", str(self.mouse_label_x) + "|" + str(
                        self.mouse_label_y) + "|" + cursor_type + "|next")
            else:
                # Получите текущее положение курсора мыши
                # x, y = pyautogui.position()
                x, y = self.mouse.position
                cursor_type = get_current_cursor()
                if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(cursor_type, str):
                    client.publish("client/mouse/position", str(x) + "|" + str(y) + "|" + cursor_type + "|last")
            self.mouse_label_x, self.mouse_label_y = -1, -1

        if message.topic == "server/quit":
            self.quit = True

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
        self.server_address = server_address
        self.server_password = server_password
        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port
        self.mqtt_timeout = mqtt_timeout
        self.client_mqqt = mqtt.Client(self.my_id, False)
        self.client_mqqt.on_connect = self.on_connect
        self.client_mqqt.on_disconnect = self.on_disconnect
        self.client_mqqt.on_message = self.on_message
        print(self.mqtt_port)
        try:
            # if self.mqtt_port == 0:
            #     self.client_mqqt.connect(self.mqtt_address)
            # elif self.mqtt_timeout == 0:
            #     self.client_mqqt.connect(self.mqtt_address, self.mqtt_port)
            # else:
            #     self.client_mqqt.connect(self.mqtt_address, self.mqtt_port, self.mqtt_timeout)

            self.client_mqqt.connect(self.mqtt_address)
            # self.client_mqqt.connect("broker.hivemq.com", 1883, 60)
            self.client_mqqt.loop_start()
            self.client_mqqt.subscribe("server/status")  # Подписываемся на сообщение с клиента о запросе статуса на подключение
            self.client_mqqt.subscribe("server/quit")  # Сообщение от клиента, что он отключается от сервера
            self.server_status = "wait"  # Сервер ожидает наверное подключения
            self.timer.start(150)  # Таймер с состоянием переменной self.server_status
            self.connect_mqtt = True  # Подключение к mqtt серверу установлено

        except:
            self.connect_mqtt = False
            print("Could not connect to the Mosquito server")

    def update_screen(self):
        if not self.connect_mqtt:  # Если соединения с сервером mqtt нет, то все игнорируем
            return
        if self.quit:  # если выход из режима сервера, то посылаем клиентам, что сервер закончил работу
            self.client_mqqt.publish("client/quit")
            time.sleep(1)
            self.timer.stop()  # Остановите таймер, если self.quit истинно
            self.client_mqqt.loop_stop()
            self.client_mqqt.disconnect()
            return
        self.client_mqqt.publish("client/status", self.server_status)
