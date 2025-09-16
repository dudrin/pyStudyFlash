import threading


class MyTimer:
    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.timer = None

    def start(self):
        # Останавливаем предыдущий таймер, если он работает
        if self.timer is not None:
            self.stop()

        # Создаем и запускаем новый таймер
        self.timer = threading.Timer(self.interval, self.callback)
        self.timer.start()

    def stop(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def isActive(self):
        return self.timer is not None and self.timer.is_alive()
