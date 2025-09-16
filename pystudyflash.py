import os
import pickle
import sys

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QToolButton, QMenu, QToolBar, \
    QMdiArea, QMdiSubWindow, QDialog, QTableWidget, QTableWidgetItem, QFormLayout, \
    QLineEdit, QHeaderView, QDialogButtonBox, QAbstractItemView, QCheckBox, QLabel, QTabWidget, QDockWidget, QHBoxLayout

from client import ScreenShareClient
from server import ScreenShareServer


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QSettings('sets/settings.ini', QSettings.Format.IniFormat)
        print(self.settings.fileName())

        self.setWindowTitle('Настройки')
        self.setGeometry(0, 0, 400, 1024)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.West)

        # Вкладка сервера
        self.server_tab = QWidget()
        self.server_address_input = QLineEdit()
        self.server_password_input = QLineEdit()
        self.server_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_password_check = QCheckBox('Показать пароль')
        self.show_password_check.toggled.connect(self.toggle_password_visibility)
        self.save_button = QPushButton('Сохранить')
        self.save_button.clicked.connect(self.save_settings)

        server_layout = QVBoxLayout()
        server_layout.addWidget(QLabel('Адрес сервера'))
        server_layout.addWidget(self.server_address_input)
        server_layout.addWidget(QLabel('Пароль сервера'))
        server_layout.addWidget(self.server_password_input)
        server_layout.addWidget(self.show_password_check)
        server_layout.addWidget(self.save_button)

        self.server_tab.setLayout(server_layout)
        self.tab_widget.addTab(self.server_tab, 'Сервер')

        self.mqtt_tab = QWidget()
        self.mqtt_address_input = QLineEdit()
        self.mqtt_port_input = QLineEdit()
        self.mqtt_timeout_input = QLineEdit()
        self.save_mqtt_button = QPushButton('Сохранить')
        self.save_mqtt_button.clicked.connect(self.save_settings)

        mqtt_layout = QVBoxLayout()
        mqtt_layout.addWidget(QLabel('MQTT сервер'))
        mqtt_layout.addWidget(QLabel('Адрес'))
        mqtt_layout.addWidget(self.mqtt_address_input)
        mqtt_layout.addWidget(QLabel('Порт'))
        mqtt_layout.addWidget(self.mqtt_port_input)
        mqtt_layout.addWidget(QLabel('Таймаут'))
        mqtt_layout.addWidget(self.mqtt_timeout_input)
        mqtt_layout.addWidget(self.save_mqtt_button)

        self.mqtt_tab.setLayout(mqtt_layout)
        self.tab_widget.addTab(self.mqtt_tab, 'MQTT')

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

        self.load_settings()

    def toggle_password_visibility(self, checked):
        self.server_password_input.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)

    def load_settings(self):
        server_address = self.settings.value('server_address', '')
        server_password = self.settings.value('server_password', '')
        mqtt_address = self.settings.value('mqtt_address', '')
        mqtt_port = self.settings.value('mqtt_port', '')
        mqtt_timeout = self.settings.value('mqtt_timeout', '')

        self.server_address_input.setText(server_address)
        self.server_password_input.setText(server_password)
        self.mqtt_address_input.setText(mqtt_address)
        self.mqtt_port_input.setText(mqtt_port)
        self.mqtt_timeout_input.setText(mqtt_timeout)

    def save_settings(self):
        server_address = self.server_address_input.text()
        server_password = self.server_password_input.text()
        mqtt_address = self.mqtt_address_input.text()
        mqtt_port = self.mqtt_port_input.text()
        mqtt_timeout = self.mqtt_timeout_input.text()

        self.settings.setValue('server_address', server_address)
        self.settings.setValue('server_password', server_password)
        self.settings.setValue('mqtt_address', mqtt_address)
        self.settings.setValue('mqtt_port', mqtt_port)
        self.settings.setValue('mqtt_timeout', mqtt_timeout)

        self.close()


class AddressBookDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ['Адрес сервера', 'Пользователь', 'Пароль', 'Группа', 'MQTT сервер', 'MQTT порт', 'MQTT таймаут'])
        
        # Fix: Ensure horizontalHeader is not None before calling setSectionResizeMode
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)  # запретить редактирование
        self.table.hideColumn(2)  # скрыть колонку пароля

        self.add_button = QPushButton('Добавить', self)
        self.add_button.clicked.connect(self.add_entry)

        self.edit_button = QPushButton('Редактировать', self)
        self.edit_button.clicked.connect(self.edit_entry)

        self.delete_button = QPushButton('Удалить', self)
        self.delete_button.clicked.connect(self.delete_entry)
        self.view_button = QPushButton('Просмотр', self)
        self.view_button.clicked.connect(lambda: self.view_entry(self.table.currentRow()))

        self.view_group_button = QPushButton('Просмотр группы', self)
        self.view_group_button.clicked.connect(self.view_group_entry)

        self.exit_button = QPushButton('Выход', self)
        self.exit_button.clicked.connect(self.close)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.view_button)
        button_layout.addWidget(self.view_group_button)
        button_layout.addWidget(self.exit_button)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.load_data()

    def view_entry(self, current_row=None):
        current_row = self.table.currentRow()
        if current_row is not None and current_row != -1:
            server_address_item = self.table.item(current_row, 0)
            server_password_item = self.table.item(current_row, 2)
            mqtt_address_item = self.table.item(current_row, 4)
            mqtt_port_item = self.table.item(current_row, 5)
            mqtt_timeout_item = self.table.item(current_row, 6)

            server_address = server_address_item.text() if server_address_item else ''
            server_password = server_password_item.text() if server_password_item else ''
            mqtt_address = mqtt_address_item.text() if mqtt_address_item else ''
            mqtt_port = int(mqtt_port_item.text()) if mqtt_port_item else 0
            mqtt_timeout = int(mqtt_timeout_item.text()) if mqtt_timeout_item else 0

            # Fix: Properly access the connect_to_server method from the parent ScreenShareApp
            # Using getattr to avoid linter issues with dynamic attribute access
            parent_app = self.parent()
            connect_method = getattr(parent_app, 'connect_to_server', None)
            if connect_method and callable(connect_method):
                connect_method(server_address, server_password, mqtt_address, mqtt_port, mqtt_timeout)
            else:
                print(f"Error: Could not access connect_to_server method. Parent type: {type(parent_app)}")

    def view_group_entry(self):
        current_row = self.table.currentRow()
        if current_row > -1:
            group_item = self.table.item(current_row, 3)
            group = group_item.text() if group_item else ''

            for row in range(self.table.rowCount()):
                row_group_item = self.table.item(row, 3)
                row_group = row_group_item.text() if row_group_item else ''

                if row_group == group:
                    self.view_entry(row)

    def load_data(self):
        if not os.path.exists('sets'):
            os.makedirs('sets')

        if os.path.exists('sets/address_book'):
            with open('sets/address_book', 'rb') as f:
                data = pickle.load(f)

            for row_data in data:
                row = self.table.rowCount()
                self.table.insertRow(row)

                for column, data in enumerate(row_data):
                    item = QTableWidgetItem(data)
                    self.table.setItem(row, column, item)

    def save_data(self):
        data = []

        for row in range(self.table.rowCount()):
            row_data = []
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                row_data.append(item.text() if item else '')
            data.append(row_data)

        with open('sets/address_book', 'wb') as f:
            pickle.dump(data, f)

    def add_entry(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.edit_entry(row)

    def edit_entry(self, current_row=None):
        current_row = self.table.currentRow()

        if current_row > -1:
            email_item = self.table.item(current_row, 0)
            username_item = self.table.item(current_row, 1)
            password_item = self.table.item(current_row, 2)
            group_item = self.table.item(current_row, 3)
            mqtt_server_item = self.table.item(current_row, 4)
            mqtt_port_item = self.table.item(current_row, 5)
            mqtt_timeout_item = self.table.item(current_row, 6)

            dialog = QDialog()
            layout = QFormLayout(dialog)

            email_edit = QLineEdit(email_item.text() if email_item else '')
            email_edit.setFixedWidth(50 * email_edit.fontMetrics().averageCharWidth())
            layout.addRow('Почта:', email_edit)

            username_edit = QLineEdit(username_item.text() if username_item else '')
            username_edit.setFixedWidth(50 * username_edit.fontMetrics().averageCharWidth())
            layout.addRow('Пользователь:', username_edit)

            password_edit = QLineEdit(password_item.text() if password_item else '')
            password_edit.setFixedWidth(50 * password_edit.fontMetrics().averageCharWidth())
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addRow('Пароль:', password_edit)

            show_password_check = QCheckBox('Показать пароль')
            show_password_check.stateChanged.connect(lambda: password_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if show_password_check.isChecked() else QLineEdit.EchoMode.Password))
            layout.addRow(show_password_check)

            group_edit = QLineEdit(group_item.text() if group_item else '')
            group_edit.setFixedWidth(50 * group_edit.fontMetrics().averageCharWidth())
            layout.addRow('Группа:', group_edit)

            mqtt_server_edit = QLineEdit(mqtt_server_item.text() if mqtt_server_item else '')
            mqtt_server_edit.setFixedWidth(50 * mqtt_server_edit.fontMetrics().averageCharWidth())
            layout.addRow('MQTT сервер:', mqtt_server_edit)

            mqtt_port_edit = QLineEdit(mqtt_port_item.text() if mqtt_port_item else '')
            mqtt_server_edit.setFixedWidth(50 * mqtt_port_edit.fontMetrics().averageCharWidth())
            layout.addRow('MQTT порт:', mqtt_port_edit)

            mqtt_timeout_edit = QLineEdit(mqtt_timeout_item.text() if mqtt_timeout_item else '')
            mqtt_timeout_edit.setFixedWidth(50 * mqtt_timeout_edit.fontMetrics().averageCharWidth())
            layout.addRow('MQTT таймаут:', mqtt_timeout_edit)

            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                                          Qt.Orientation.Horizontal, dialog)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addRow(button_box)

            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                self.table.setItem(current_row, 0, QTableWidgetItem(email_edit.text()))
                self.table.setItem(current_row, 1, QTableWidgetItem(username_edit.text()))
                self.table.setItem(current_row, 2, QTableWidgetItem(password_edit.text()))
                self.table.setItem(current_row, 3, QTableWidgetItem(group_edit.text()))
                self.table.setItem(current_row, 4, QTableWidgetItem(mqtt_server_edit.text()))
                self.table.setItem(current_row, 5, QTableWidgetItem(mqtt_port_edit.text()))
                self.table.setItem(current_row, 6, QTableWidgetItem(mqtt_timeout_edit.text()))

                self.save_data()

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def delete_entry(self):
        current_row = self.table.currentRow()
        if current_row > -1:
            self.table.removeRow(current_row)
        self.save_data()


class ScreenShareApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings_dialog = SettingsDialog(self)  # Создаем объект установки
        self.settings_toolbar = QToolBar()
        self.settings_toolbar.addWidget(self.settings_dialog)  # Создать в тулбар пункт Установки

        self.settings_dock = QDockWidget()
        self.settings_dock.setWidget(self.settings_toolbar)  # И поместить в доквиджет

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.settings_dock)  # и поместить в левую часть экрана
        self.settings_dock.hide()  # Скрыть доквиджет установок

        self.settings = QSettings('sets/settings.ini', QSettings.Format.IniFormat)  # ссылка на файл установок
        self.pub_server_address = self.settings.value('server_address', '')  # Считать параметры из файла настроек или оставить пустыми
        self.pub_server_password = self.settings.value('server_password', '')
        self.pub_mqtt_address = self.settings.value('mqtt_address', '')
        self.pub_mqtt_port = self.settings.value('mqtt_port', '')
        self.pub_mqtt_timeout = self.settings.value('mqtt_timeout', '')

        self.dialog = AddressBookDialog(self)  # Создать объект адресной книги
        self.server = None
        self.servers = {}  # словарь для хранения серверов

        # Создайте поле ввода для адреса сервера
        self.server_address_input = QLineEdit(self)
        self.server_address_input.setPlaceholderText('Введите адрес сервера')

        # Создайте кнопку для подключения к серверу
        self.connect_button = QPushButton('Подключиться', self)
        self.connect_button.clicked.connect(self.connect_to_server)

        # Создайте меню
        self.menu = QMenu(self)
        self.menu_action_settings = QAction('Настройки', self)
        self.menu_action_settings.triggered.connect(self.open_settings)
        self.menu_action_address_book = QAction('Адресная книга', self)
        self.menu_action_address_book.triggered.connect(self.open_address_book)
        self.menu_action_help = QAction('Помощь', self)
        self.menu_action_about = QAction('Об pyStudyFlash', self)
        self.menu_action_exit = QAction('Выход', self)

        self.menu.addAction(self.menu_action_settings)
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

        self.start_server_button = QPushButton('Старт доступ', self)
        self.start_server_button.clicked.connect(self.start_pub_server)  # Запустить сервер предоставления экрана для этого компьютера

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

    def open_settings(self):
        self.settings_dock.show()

    def start_pub_server(self):  # Запускает сервер доступа к экрану компьютера
        self.server = ScreenShareServer()  # Экземпляр текущего сервера
        if len(self.pub_server_address) > 0 and len(self.pub_server_password) > 0:
            self.server.show()
            self.server.run(self.pub_server_address, self.pub_server_password, self.pub_mqtt_address, self.pub_mqtt_port, self.pub_mqtt_timeout)

    def connect_to_server(self, server_address='address@mail.com', server_password='', mqtt_address='', mqtt_port=0,
                          mqtt_timeout=0):
        client = ScreenShareClient()  # Создайте новый экземпляр ScreenShareClient
        client.server_address = server_address
        client.server_password = server_password
        client.mqtt_address = mqtt_address
        client.mqtt_port = mqtt_port
        client.mqtt_timeout = mqtt_timeout
        # Создайте подокно для этого сервера
        self.servers[server_address] = QMdiSubWindow()  # Добавьте новый сервер в список
        self.servers[server_address].setWindowTitle(server_address)  # Используйте адрес сервера в качестве заголовка
        self.servers[server_address].setWidget(client)  # Замените QLabel на экземпляр ScreenShareClient
        self.mdi_area.addSubWindow(self.servers[server_address])
        self.servers[server_address].show()

    def open_address_book(self):
        self.dialog.exec()


def main():
    app = QApplication(sys.argv)
    screenshare_app = ScreenShareApp()
    screenshare_app.showMaximized()  # Показать окно на весь экран
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
