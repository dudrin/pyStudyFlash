import paho.mqtt.client as mqtt
import time
import uuid
import cv2
import mss
from PyQt6.QtGui import QAction
from mss.tools import zlib
import numpy
import base64
import io
import pickle
from PyQt6 import QtWidgets, QtGui, QtCore

outup = False
size = False
capture = False
width = 0
height = 0
last_image = None
first = False


def on_connect(client, userdata, flags, rc):
    print("Connected flags " + str(flags) + " ,result code=" + str(rc))


def on_message(client, userdata, message):
    global outup
    global size
    global capture
    global width
    global height
    global last_image
    global first

    if message.topic == "client/size":
        if width == 0 and height == 0:
            strsize = message.payload.decode("utf-8")
            strlist = strsize.split("|")
            width = int(strlist[0])
            height = int(strlist[1])
            size = True

    if message.topic == "client/update/first":
        # stay synchronized with other connected clients
        if size == True:
            DecodeAndShowPayload(message, False)
            first = True

    if message.topic == "client/update/next":
        # stay synchronized with other connected clients
        if size == True and first == True:
            DecodeAndShowPayload(message)

    if message.topic == "client/quit":
        outup = True


def DecodeAndShowPayload(message, NextFrame=True):
    global last_image
    global capture
    global outup

    if NextFrame == True:
        # subsequent image - delta that brings much better compression ratio as unchanged RGBA quads will XOR to 0,0,0,0
        xor_image = pickle.loads(zlib.decompress(base64.b64decode(message.payload.decode("utf-8")), 15, 65535))
        image = last_image ^ xor_image
    else:
        # first image - less compression than delta
        image = pickle.loads(zlib.decompress(base64.b64decode(message.payload.decode("utf-8")), 15, 65535))
    last_image = image

    window.viewer.update_image(image)


class ImageViewer(QtWidgets.QGraphicsView):
    def __init__(self):
        super(ImageViewer, self).__init__()
        self.scene = QtWidgets.QGraphicsScene()
        self.setScene(self.scene)
        self.image_item = QtWidgets.QGraphicsPixmapItem()
        self.scene.addItem(self.image_item)

    def update_image(self, cv_img):
        print("Декодируем!!!")
        qt_img = self.convert_cv_qt(cv_img)
        pixmap = QtGui.QPixmap.fromImage(qt_img)
        self.image_item.setPixmap(pixmap)

    @staticmethod
    def convert_cv_qt(cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(640, 480, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        return p


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.viewer = ImageViewer()
        self.setCentralWidget(self.viewer)

        # Добавьте кнопку на панель инструментов для запуска отображения изображения
        self.toolbar = self.addToolBar("Toolbar")
        self.start_action = QAction("Start", self)
        self.start_action.triggered.connect(self.start_mqtt)
        self.toolbar.addAction(self.start_action)

    def start_mqtt(self):
        global outup
        global size
        global capture
        global width
        global height
        global last_image
        global first

        myid = str(uuid.uuid4()) + str(time.time())
        print("Client Id = " + myid)
        client = mqtt.Client(myid, False)
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect("127.0.0.1")
            client.loop_start()
            client.subscribe("client/size")
            client.subscribe("client/update/first")
            client.subscribe("client/update/next")
            client.subscribe("client/quit")

            # ask once and retain in case client starts before server
            asksize = False
            while not size:
                if not asksize:
                    client.publish("server/size", "1", 0, True)
                    asksize = True
                time.sleep(1)

            first_image = True
            while not outup:
                if not capture:
                    capture = True
                    if first_image:
                        client.publish("server/update/first")
                        first_image = False
                    else:
                        client.publish("server/update/next")
                time.sleep(.1)

            client.loop_stop()
            client.disconnect()
        except Exception as e:
            print("Could not connect to the Mosquito server")
            print("Error: ", str(e))


app = QtWidgets.QApplication([])
window = MainWindow()
window.show()
app.exec()
