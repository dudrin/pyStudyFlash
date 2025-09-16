import paho.mqtt.client as mqtt
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QGraphicsView
import pyautogui

class CustomView(QGraphicsView):
    def __init__(self, mqtt_client):
        super(CustomView, self).__init__()
        self.mqtt_client = mqtt_client

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            print(f'Нажата правая кнопка мыши в позиции ({event.position().x()}, {event.position().y()})')
            self.mqtt_client.publish("mouse/right_click", f"({event.position().x()}, {event.position().y()})")
        elif event.button() == Qt.MouseButton.LeftButton:
            print(f'Нажата левая кнопка мыши в позиции ({event.position().x()}, {event.position().y()})')
            self.mqtt_client.publish("mouse/left_click", f"({event.position().x()}, {event.position().y()})")
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        print(f'Двойной клик мыши в позиции ({event.position().x()}, {event.position().position().y()})')
        self.mqtt_client.publish("mouse/double_click", f"({event.position().x()}, {event.position().y()})")
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        degrees = event.angleDelta().y() / 8  # Преобразуем в градусы
        steps = degrees / 15  # Преобразуем в шаги
        print(f'Вращение колесика мыши: {steps} шагов')
        self.mqtt_client.publish("mouse/wheel", f"{steps} steps")
        super().wheelEvent(event)

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("#")

def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    if msg.topic == "mouse/right_click":
        x, y = map(int, msg.payload.decode()[1:-1].split(', '))
        pyautogui.rightClick(x, y)
    elif msg.topic == "mouse/left_click":
        x, y = map(int, msg.payload.decode()[1:-1].split(', '))
        pyautogui.click(x, y)
    elif msg.topic == "mouse/double_click":
        x, y = map(int, msg.payload.decode()[1:-1].split(', '))
        pyautogui.doubleClick(x, y)
    elif msg.topic == "mouse/wheel":
        steps = int(float(msg.payload.decode().split(' ')[0]))
        pyautogui.scroll(steps)

# Создаем клиента MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)  # Замените на ваш MQTT брокер

app = QApplication([])
view = CustomView(client)
view.show()

client.loop_start()
app.exec()
client.loop_stop()
