import os
import pickle
import sys

from PyQt6.QtCore import Qt, QSettings, QEvent, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QCursor
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QToolButton, QMenu, QToolBar, \
    QMdiArea, QMdiSubWindow, QDialog, QTableWidget, QTableWidgetItem, QFormLayout, \
    QLineEdit, QHeaderView, QDialogButtonBox, QAbstractItemView, QCheckBox, QLabel, QTabWidget, QDockWidget, QHBoxLayout, QFrame

from app_paths import address_book_file_path, settings_file_path


def _get_client_class():
    # Import client lazily so Qt initializes before win32 DPI side effects from dependencies.
    from client import ScreenShareClient
    return ScreenShareClient


def _get_server_class():
    # Import server lazily so Qt initializes before win32 DPI side effects from dependencies.
    from server import ScreenShareServer
    return ScreenShareServer


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QSettings(settings_file_path(), QSettings.Format.IniFormat)
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
        address_book_path = address_book_file_path()
        if os.path.exists(address_book_path):
            with open(address_book_path, 'rb') as f:
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

        with open(address_book_file_path(), 'wb') as f:
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


class ViewerHostWindow(QMainWindow):
    def __init__(self, server_key, on_close):
        super().__init__()
        self._server_key = server_key
        self._on_close = on_close
        self._fullscreen_mode = False
        self._normal_geometry = None
        self._normal_window_state = Qt.WindowState.WindowNoState
        self._normal_window_flags = self.windowFlags()

        self._overlay = QFrame(self)
        self._overlay.setFrameShape(QFrame.Shape.StyledPanel)
        self._overlay.setStyleSheet(
            "QFrame { background: rgba(30, 30, 30, 220); color: white; border: 1px solid #505050; }"
            "QPushButton { background: #444; color: white; border: 1px solid #666; padding: 4px 10px; }"
            "QPushButton:hover { background: #555; }"
        )
        overlay_layout = QHBoxLayout(self._overlay)
        overlay_layout.setContentsMargins(8, 6, 8, 6)
        overlay_layout.setSpacing(8)
        overlay_label = QLabel("Fullscreen mode")
        overlay_hint = QLabel("Ctrl+Tab to exit")
        overlay_exit = QPushButton("Exit Fullscreen")
        overlay_exit.clicked.connect(self.exit_fullscreen_mode)
        overlay_layout.addWidget(overlay_label)
        overlay_layout.addStretch(1)
        overlay_layout.addWidget(overlay_hint)
        overlay_layout.addWidget(overlay_exit)
        self._overlay.hide()
        self._overlay.raise_()

        self._overlay_hide_timer = QTimer(self)
        self._overlay_hide_timer.setSingleShot(True)
        self._overlay_hide_timer.timeout.connect(self._overlay.hide)

        self._overlay_hover_timer = QTimer(self)
        self._overlay_hover_timer.setInterval(120)
        self._overlay_hover_timer.timeout.connect(self._refresh_overlay_hover)

        self._fullscreen_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        self._fullscreen_shortcut.activated.connect(self.exit_fullscreen_mode)
        self._fullscreen_shortcut.setEnabled(False)

        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setMouseTracking(True)
        self.installEventFilter(self)

    def set_client_widget(self, widget):
        old_widget = self.centralWidget()
        if old_widget is not None:
            old_widget.removeEventFilter(self)
        self.setCentralWidget(widget)
        if widget is not None:
            widget.setMouseTracking(True)
            widget.installEventFilter(self)
            bind = getattr(widget, 'set_viewer_window', None)
            if callable(bind):
                bind(self)
            notify = getattr(widget, 'on_viewer_fullscreen_changed', None)
            if callable(notify):
                notify(self._fullscreen_mode)

    def is_fullscreen_mode(self):
        return self._fullscreen_mode

    def toggle_fullscreen_mode(self):
        if self._fullscreen_mode:
            self.exit_fullscreen_mode()
        else:
            self.enter_fullscreen_mode()

    def _notify_fullscreen_state(self):
        widget = self.centralWidget()
        if widget is None:
            return
        notify = getattr(widget, 'on_viewer_fullscreen_changed', None)
        if callable(notify):
            notify(self._fullscreen_mode)

    def enter_fullscreen_mode(self):
        if self._fullscreen_mode:
            return
        self._fullscreen_mode = True
        self._normal_geometry = self.geometry()
        self._normal_window_state = self.windowState()
        self._normal_window_flags = self.windowFlags()
        fullscreen_flags = (
            self._normal_window_flags
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowFlags(fullscreen_flags)
        screen = QApplication.screenAt(QCursor.pos())
        if screen is not None and self.windowHandle() is not None:
            self.windowHandle().setScreen(screen)
        self.showFullScreen()
        self._activate_fullscreen_window()
        QTimer.singleShot(80, self._activate_fullscreen_window)
        self._fullscreen_shortcut.setEnabled(True)
        self._overlay_hover_timer.start()
        self._position_overlay()
        self._show_overlay_temporarily()
        self._notify_fullscreen_state()

    def exit_fullscreen_mode(self):
        if not self._fullscreen_mode:
            return
        self._fullscreen_mode = False
        self._fullscreen_shortcut.setEnabled(False)
        self._overlay_hover_timer.stop()
        self._overlay_hide_timer.stop()
        self._overlay.hide()
        self.setWindowFlags(self._normal_window_flags)
        self.showNormal()
        if self._normal_window_state == Qt.WindowState.WindowMaximized:
            self.showMaximized()
        elif self._normal_geometry is not None:
            self.setGeometry(self._normal_geometry)
        self.show()
        self.raise_()
        self.activateWindow()
        self._notify_fullscreen_state()

    def _position_overlay(self):
        if not self._overlay.isVisible() and not self._fullscreen_mode:
            return
        width = max(300, self.width())
        height = 46
        self._overlay.setGeometry(0, 0, width, height)
        self._overlay.raise_()

    def _show_overlay_temporarily(self):
        if not self._fullscreen_mode:
            return
        self._position_overlay()
        self._overlay.show()
        self._overlay.raise_()
        self._overlay_hide_timer.start(1800)

    def _refresh_overlay_hover(self):
        if not self._fullscreen_mode:
            return
        local_pos = self.mapFromGlobal(QCursor.pos())
        if 0 <= local_pos.x() <= self.width() and 0 <= local_pos.y() <= 4:
            self._show_overlay_temporarily()

    def _activate_fullscreen_window(self):
        self.raise_()
        self.activateWindow()
        handle = self.windowHandle()
        if handle is not None:
            handle.requestActivate()

    def eventFilter(self, watched, event):
        if self._fullscreen_mode and event.type() in {QEvent.Type.MouseMove, QEvent.Type.Enter}:
            self._refresh_overlay_hover()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fullscreen_mode:
            self._position_overlay()

    def keyPressEvent(self, event):
        if self._fullscreen_mode:
            is_ctrl_tab = (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_Tab
            if is_ctrl_tab:
                self.exit_fullscreen_mode()
                event.accept()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if self._fullscreen_mode:
            self.exit_fullscreen_mode()
        client_widget = self.centralWidget()
        if client_widget is not None:
            stop_stream = getattr(client_widget, 'stop_stream', None)
            if callable(stop_stream):
                try:
                    stop_stream()
                except Exception:
                    pass
        if callable(self._on_close):
            self._on_close(self._server_key, self)
        super().closeEvent(event)


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

        self.settings = QSettings(settings_file_path(), QSettings.Format.IniFormat)  # ссылка на файл установок
        # Считать параметры из файла настроек с явным указанием типа
        self.pub_server_address = str(self.settings.value('server_address', '', type=str) or '')
        self.pub_server_password = str(self.settings.value('server_password', '', type=str) or '')
        self.pub_mqtt_address = str(self.settings.value('mqtt_address', '', type=str) or '')
        self.pub_mqtt_port = self.settings.value('mqtt_port', 0, type=int)
        self.pub_mqtt_timeout = self.settings.value('mqtt_timeout', 0, type=int)

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

    def start_pub_server(self):  # ????????? ?????? ??????? ? ?????? ??????????
        if self.server is None:
            self.server = _get_server_class()(app_manager=self)  # ????????? ???????? ???????
        settings = getattr(self, 'settings', None)
        if settings is not None:
            self.pub_server_address = str(settings.value('server_address', self.pub_server_address, type=str) or '').strip()
            self.pub_server_password = str(settings.value('server_password', self.pub_server_password, type=str) or '').strip()
            self.pub_mqtt_address = str(settings.value('mqtt_address', self.pub_mqtt_address, type=str) or '').strip()
            self.pub_mqtt_port = settings.value('mqtt_port', self.pub_mqtt_port, type=int)
            self.pub_mqtt_timeout = settings.value('mqtt_timeout', self.pub_mqtt_timeout, type=int)
        server_address = str(self.pub_server_address or '').strip()
        server_password = str(self.pub_server_password or '').strip()
        mqtt_address = str(self.pub_mqtt_address or '').strip() or 'broker.hivemq.com'
        try:
            mqtt_port = int(str(self.pub_mqtt_port or '').strip() or 0)
        except ValueError:
            mqtt_port = 0
        try:
            mqtt_timeout = int(str(self.pub_mqtt_timeout or '').strip() or 0)
        except ValueError:
            mqtt_timeout = 0
        self.server.show()
        if not mqtt_address:
            print('MQTT ????? ?? ?????, ?????? ?? ???????')
            return
        self.server.run(server_address, server_password, mqtt_address, mqtt_port, mqtt_timeout)

    def connect_to_server(self, server_address='address@mail.com', server_password='', mqtt_address='', mqtt_port=0,
                          mqtt_timeout=0):
        # Когда метод вызывается без аргументов, используем UI и сохранённые настройки
        if server_address == 'address@mail.com' and not server_password and not mqtt_address and mqtt_port == 0 and mqtt_timeout == 0:
            address_input = self.server_address_input.text().strip() if hasattr(self, 'server_address_input') else ''
            settings = getattr(self, 'settings', None)
            if settings is not None:
                # Use UI input if provided, otherwise use settings
                # Explicitly convert QSettings values to proper types with type=str to prevent bool conversion
                server_address = address_input or str(settings.value('server_address', '', type=str))
                server_password = str(settings.value('server_password', '', type=str))
                mqtt_address = str(settings.value('mqtt_address', '', type=str))
                mqtt_port = settings.value('mqtt_port', 0, type=int)
                mqtt_timeout = settings.value('mqtt_timeout', 0, type=int)
                
                # Debug output
                print(f"Client configuration:")
                print(f"  UI input: '{address_input}'")
                print(f"  Using server_address: '{server_address}'")
                print(f"  Using server_password: '{server_password}'")
                print(f"  Using mqtt_address: '{mqtt_address}'")
                print(f"  Topic prefix will be: '{server_address}/{server_password}'")
            else:
                server_address = address_input
                server_password = ''
                mqtt_address = ''
                mqtt_port = 0
                mqtt_timeout = 0
        
        mqtt_port = int(str(mqtt_port).strip() or 0)
        mqtt_timeout = int(str(mqtt_timeout).strip() or 0)
        
        # Validate server_address is a non-empty string
        if not server_address or not isinstance(server_address, str):
            print(f"Invalid server_address: {server_address} (type: {type(server_address)})")
            server_address = 'Unknown Server'
        
        client = _get_client_class()()
        client.server_address = server_address
        client.server_password = server_password
        client.mqtt_address = mqtt_address
        client.mqtt_port = mqtt_port
        client.mqtt_timeout = mqtt_timeout
        client.user_initiated_close = False

        existing_window = self.servers.get(server_address)
        if existing_window is not None:
            try:
                existing_window.close()
            except Exception:
                pass

        viewer_window = ViewerHostWindow(server_address, self._on_viewer_window_closed)
        viewer_window.setWindowTitle(str(server_address))
        viewer_window.resize(1100, 700)
        viewer_window.set_client_widget(client)
        bind_viewer_window = getattr(client, 'set_viewer_window', None)
        if callable(bind_viewer_window):
            bind_viewer_window(viewer_window)
        self.servers[server_address] = viewer_window
        viewer_window.show()
        viewer_window.raise_()
        viewer_window.activateWindow()
        client.start_stream()

    def _on_viewer_window_closed(self, server_key, window):
        current = self.servers.get(server_key)
        if current is window:
            self.servers.pop(server_key, None)

    def get_address_book_entry(self, identifier):
        if not identifier:
            return None
        identifier = identifier.strip().lower()
        table = getattr(self.dialog, 'table', None)
        if table is None:
            return None
        def _text(item):
            return item.text().strip() if item else ''
        def _parse_int(value):
            try:
                return int(str(value).strip() or 0)
            except (TypeError, ValueError):
                return 0
        for row in range(table.rowCount()):
            server_item = table.item(row, 0)
            user_item = table.item(row, 1)
            server_value = _text(server_item).lower()
            user_value = _text(user_item).lower()
            if identifier in {server_value, user_value}:
                password_item = table.item(row, 2)
                mqtt_address_item = table.item(row, 4)
                mqtt_port_item = table.item(row, 5)
                mqtt_timeout_item = table.item(row, 6)
                return {
                    'server_address': _text(server_item),
                    'username': _text(user_item),
                    'password': _text(password_item),
                    'mqtt_address': _text(mqtt_address_item),
                    'mqtt_port': _parse_int(_text(mqtt_port_item)),
                    'mqtt_timeout': _parse_int(_text(mqtt_timeout_item))
                }
        return None

    def open_address_book(self):
        self.dialog.exec()


def main():
    app = QApplication(sys.argv)
    screenshare_app = ScreenShareApp()
    screenshare_app.showMaximized()  # Показать окно на весь экран
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

