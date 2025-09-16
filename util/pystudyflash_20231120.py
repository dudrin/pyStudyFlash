import sys

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QToolButton, QMenu, QLineEdit, \
    QToolBar, QMdiSubWindow, QMdiArea
from server import ScreenShareServer
from client import ScreenShareClient


class ScreenShareApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.server = None
        self.clients = []  # Список для хранения клиентов

        # Создайте поле ввода для адреса сервера
        self.server_address_input = QLineEdit(self)
        self.server_address_input.setPlaceholderText('Введите адрес сервера')

        # Создайте кнопку для подключения к серверу
        self.connect_button = QPushButton('Подключиться', self)
        self.connect_button.clicked.connect(self.connect_to_server)

        # Создайте меню
        self.menu = QMenu(self)
        self.menu_action_settings = QAction('Настройки', self)
        self.menu_action_change_password = QAction('Изменить пароль доступа', self)
        self.menu_action_address_book = QAction('Адресная книга', self)
        self.menu_action_help = QAction('Помощь', self)
        self.menu_action_about = QAction('Об pyStudyFlash', self)
        self.menu_action_exit = QAction('Выход', self)

        self.menu.addAction(self.menu_action_settings)
        self.menu.addAction(self.menu_action_change_password)
        self.menu.addAction(self.menu_action_address_book)
        self.menu.addAction(self.menu_action_help)
        self.menu.addAction(self.menu_action_about)
        self.menu.addAction(self.menu_action_exit)

        # Создайте кнопку меню
        self.menu_button = QToolButton(self)
        self.menu_button.setText('☰')  # Используйте символ "☰" в качестве иконки меню
        self.menu_button.setMenu(self.menu)
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        # Создайте панель инструментов и добавьте виджеты
        self.toolbar = QToolBar(self)
        self.toolbar.addWidget(self.server_address_input)
        self.toolbar.addWidget(self.connect_button)
        self.toolbar.addWidget(self.menu_button)

        # Добавьте панель инструментов в верхнюю часть окна
        self.addToolBar(self.toolbar)

        # Создайте область MDI для отображения подокон серверов
        self.mdi_area = QMdiArea()

        self.start_server_button = QPushButton('Start Screen Share Server', self)
        self.start_server_button.clicked.connect(self.start_server)

        # Установите макет для размещения виджетов
        layout = QVBoxLayout()
        layout.addWidget(self.start_server_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)

        # Создайте общий макет для размещения mdi_area и central_widget
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.mdi_area)
        main_layout.addWidget(central_widget)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def start_server(self):
        self.server = ScreenShareServer()
        self.server.show()
        self.server.run()

    def connect_to_server(self):
        server_address = self.server_address_input.text()
        print(f'Подключение к серверу по адресу {server_address}')
        client = ScreenShareClient()  # Создайте новый экземпляр ScreenShareClient
        client.show()
        self.clients.append(client)  # Добавьте нового клиента в список

        # Создайте подокно для этого сервера
        subwindow = QMdiSubWindow()
        subwindow.setWindowTitle(server_address)  # Используйте адрес сервера в качестве заголовка
        subwindow.setWidget(client)  # Замените QLabel на экземпляр ScreenShareClient
        self.mdi_area.addSubWindow(subwindow)
        subwindow.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    screenshare_app = ScreenShareApp()
    screenshare_app.showMaximized()  # Показать окно на весь экран
    sys.exit(app.exec())
