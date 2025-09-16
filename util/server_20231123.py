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
        self.monitor = 0  # all monitors
        self.quit, self.capture, self.last_image = False, False, None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_screen)

        self.listener = mouse_move.Listener(on_move=self.on_move)
        self.listener.start()
        self.mouse_move_on_server = False
        self.timer_block_mouse_client = MyTimer(5.0, self.on_timer)  # Создаем таймер на 5 секунд

        self.keyboard = Controller()
        self.mouse = MouseController()

        self.setMouseTracking(True)

        self.mouse_label_x, self.mouse_label_y = -1, -1

        self.my_id = str(uuid.uuid4()) + str(time.time())
        print("Client Id = " + self.my_id)
        self.client = ""

        self.mouse_released = False  # показывает, что левая кнопка мыши отжата
        self.mouse_move = False  # мышь на клиенте в движении

    def on_move(self, x, y):
        if not self.mouse_move:  # Если на клиенте не перемещается мышь
            print('!', self.mouse_move)
            if not self.timer_block_mouse_client.isActive():  # Проверяем, работает ли таймер
                self.mouse_move_on_server = True  # Пока True клиент не сможет управлять мышью на сервере
                self.timer_block_mouse_client.start()
        self.mouse_move = False

    def on_timer(self):
        print('Сработал таймер', time.time())
        self.timer_block_mouse_client.stop()
        self.mouse_move_on_server = False  # Клиенту разрешено управлять мышью сервера

    def on_connect(self, client, userdata, flags, rc):
        print("Connected flags " + str(flags) + " ,result code=" + str(rc))

    def on_disconnect(self, client, userdata, flags, rc):
        print("Disconnected flags " + str(flags) + " ,result code=" + str(rc))

    def on_message(self, client, userdata, message):
        if message.topic == "server/size":
            with mss.mss() as sct:
                sct_img = sct.grab(sct.monitors[self.monitor])
                size = sct_img.size
                client.publish("client/size", str(size.width) + "|" + str(size.height))

        if message.topic == "server/keyboard/keypress":
            key_sequence = message.payload.decode()
            print(message.topic + " " + str(key_sequence))
            keys = key_sequence.split('+')

            # Если ключ содержит более одного символа, это специальная клавиша
            if len(keys) == 1 and len(keys[0]) > 1 and not keys[0].lower() == 'plus':
                if keys[0].lower() == 'plus':
                    keys[0] = '+'
                if keys[0].lower() == 'numlock':
                    keys[0] = 'num_lock'
                if keys[0].lower() == 'pgdown':
                    keys[0] = 'page_down'
                if keys[0].lower() == 'pgup':
                    keys[0] = 'page_up'
                if keys[0].lower() == 'return':
                    keys[0] = 'enter'
                self.keyboard.press(getattr(Key, keys[0]))
                self.keyboard.release(getattr(Key, keys[0]))
            elif '+' in key_sequence:
                # Если одним из ключей является 'shift' и есть только один другой ключ, который является буквой длиной 1, используем копирование и вставку
                if 'shift' in keys and len(keys) == 2 and len(keys[1]) == 1 and keys[1].isalpha():
                    pyperclip.copy(keys[1].upper())
                    self.keyboard.press(Key.ctrl)
                    self.keyboard.press('v')
                    self.keyboard.release('v')
                    self.keyboard.release(Key.ctrl)
                else:
                    for key in keys:
                        if not keys[1].lower() == 'ctrl_l':
                            if len(key) > 1:
                                print(getattr(Key, key))
                                self.keyboard.press(getattr(Key, key))
                            else:
                                self.keyboard.press(key)
                    time.sleep(0.1)
                    for key in reversed(keys):
                        if not keys[1].lower() == 'ctrl_l':
                            if len(key) > 1:
                                self.keyboard.release(getattr(Key, key))
                            else:
                                self.keyboard.release(key)
            else:
                if keys[0].lower() == 'plus':
                    key_sequence = '+'
                pyperclip.copy(key_sequence)
                self.keyboard.press(Key.ctrl)
                self.keyboard.press('v')
                self.keyboard.release('v')
                self.keyboard.release(Key.ctrl)
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

    def BuildPayload(self, next_frame=True):
        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[self.monitor])
            image = numpy.array(sct_img)
            if next_frame:
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

    def run(self):
        self.client = mqtt.Client(self.my_id, False)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        try:
            # self.client.connect("10.1.1.66")
            self.client.connect("broker.hivemq.com", 1883, 60)
            self.client.loop_start()
            self.client.subscribe("server/size")
            self.client.subscribe("server/update/first")
            self.client.subscribe("server/update/next")
            self.client.subscribe("server/keyboard/keypress")
            self.client.subscribe("server/keyboard/keyrelease")
            self.client.subscribe("server/mouse/position")
            self.client.subscribe("server/mouse/label")
            self.client.subscribe("server/mouse/right_click")
            self.client.subscribe("server/mouse/left_click")
            self.client.subscribe("server/mouse/double_click")
            self.client.subscribe("server/mouse/wheel")
            self.client.subscribe("server/mouse/drag_start")
            self.client.subscribe("server/mouse/move")
            self.client.subscribe("server/mouse/drag_end")
            self.client.subscribe("server/quit")
            self.timer.start(1000)  # Запустите таймер при запуске
        except:
            print("Could not connect to the Mosquito server")

    def update_screen(self):
        if self.quit:
            self.client.publish("client/quit")
            time.sleep(1)
            self.timer.stop()  # Остановите таймер, если self.quit истинно
            self.client.loop_stop()
            self.client.disconnect()
            return


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     server = ScreenShareServer()
#     server.show()
#     server.run()
#     sys.exit(app.exec())
