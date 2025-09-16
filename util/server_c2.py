import paho.mqtt.client as mqtt
import time
import uuid
import cv2
import mss
import pyautogui
from mss.tools import zlib
import numpy
import base64
import io
import pickle

monitor = 0  # all monitors
outup = False
capture = False


def on_connect(client, userdata, flags, rc):
    print("Connected flags " + str(flags) + " ,result code=" + str(rc))


def on_disconnect(client, userdata, flags, rc):
    print("Disconnected flags " + str(flags) + " ,result code=" + str(rc))


def on_message(client, userdata, message):
    global outup
    global capture
    global last_image

    if message.topic == "server/size":
        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[monitor])
            size = sct_img.size
            client.publish("client/size", str(size.width) + "|" + str(size.height))

    if message.topic == "server/update/first":
        with mss.mss() as sct:
            b64img = BuildPayload(False)
            client.publish("client/update/first", b64img)

    if message.topic == "server/update/next":
        with mss.mss() as sct:
            b64img = BuildPayload()
            client.publish("client/update/next", b64img)

    if message.topic == "server/quit":
        outup = True


def BuildPayload(NextFrame=True):
    global last_image
    with mss.mss() as sct:
        sct_img = sct.grab(sct.monitors[monitor])
        image = numpy.array(sct_img)
        if NextFrame == True:
            # subsequent image - delta that brings much better compression ratio as unchanged RGBA quads will XOR to 0,0,0,0
            xor_image = image ^ last_image
            b64img = base64.b64encode(zlib.compress(pickle.dumps(xor_image), 9))
        else:
            # first image - less compression than delta
            b64img = base64.b64encode(zlib.compress(pickle.dumps(image), 9))
            print("Source Image Size=" + str(len(sct_img.rgb)))

        last_image = image
        # print("Compressed Image Size=" + str(len(b64img)) + " bytes")
        return b64img


myid = str(uuid.uuid4()) + str(time.time())
print("Client Id = " + myid)
client = mqtt.Client(myid, False)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
try:
    client.connect("127.0.0.1")
    client.loop_start()
    client.subscribe("server/size")
    client.subscribe("server/update/first")
    client.subscribe("server/update/next")
    client.subscribe("server/quit")
    while not outup:
        time.sleep(5)
        continue
    client.publish("client/quit")
    time.sleep(5)
    client.loop_stop()
    client.disconnect()
except:
    print("Could not connect to the Mosquito server")
