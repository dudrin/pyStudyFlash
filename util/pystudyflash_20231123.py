import os
import pickle
import sys

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QToolButton, QMenu, QLineEdit, \
    QToolBar, QMdiArea, QMdiSubWindow, QDialog, QTableWidget, QTableWidgetItem, QGroupBox, QFormLayout, \
    QLineEdit, QButtonGroup, QRadioButton, QHBoxLayout, QMessageBox, QInputDialog, QHeaderView, QComboBox, \
    QDialogButtonBox, QAbstractItemView, QCheckBox, QStyledItemDelegate
from PyQt6.QtCore import Qt
from server import ScreenShareServer
from client import ScreenShareClient


class AddressBookDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ['Почта', 'Пользователь', 'Пароль', 'Группа'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)  # запретить редактирование
        self.table.hideColumn(2)  # скрыть колонку пароля

        self.add_button = QPushButton('Добавить', self)
        self.add_button.clicked.connect(self.add_entry)

        self.edit_button = QPushButton('Редактировать', self)
        self.edit_button.clicked.connect(self.edit_entry)

        self.delete_button = QPushButton('Удалить', self)
        self.delete_button.clicked.connect(self.delete_entry)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addWidget(self.add_button)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

        self.load_data()

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
        self.menu_action_address_book.triggered.connect(self.open_address_book)
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

    def open_address_book(self):
        self.dialog = AddressBookDialog()
        self.dialog.exec()

    def connect_to_group(self, group):
        # Получите все строки в таблице
        rows = self.dialog.table.rowCount()

        # Пройдите по каждой строке и проверьте, соответствует ли группа указанной группе
        for row in range(rows):
            group_item = self.dialog.table.item(row, 3)  # Группа находится в четвертой колонке
            if group_item and group_item.text() == group:
                # Если группа соответствует, получите адрес сервера и подключитесь к серверу
                server_address_item = self.dialog.table.item(row, 0)  # Адрес сервера находится в первой колонке
                password_item = self.dialog.table.item(row, 2)  # Пароль находится в третьей колонке
                if server_address_item and password_item:
                    server_address = server_address_item.text()
                    password = password_item.text()
                    self.connect_to_server(server_address, password)

    # def connect_to_server(self, server_address, password):
    #     print(f'Подключение к серверу по адресу {server_address} с паролем {password}')
    #     client = ScreenShareClient()  # Создайте новый экземпляр ScreenShareClient
    #     client.show()
    #     self.clients.append(client)  # Добавьте нового клиента в список
    #
    #     # Создайте подокно для этого сервера
    #     subwindow = QMdiSubWindow()
    #     subwindow.setWindowTitle(server_address)  # Используйте адрес сервера в качестве заголовка
    #     subwindow.setWidget(client)  # Замените QLabel на экземпляр ScreenShareClient
    #     self.mdi_area.addSubWindow(subwindow)
    #     subwindow.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    screenshare_app = ScreenShareApp()
    screenshare_app.showMaximized()  # Показать окно на весь экран
    sys.exit(app.exec())
