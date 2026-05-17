# pyStudyFlash

pyStudyFlash - приложение на базе PyQt6 для демонстрации экрана и удаленного управления. Для обмена данными между сервером и клиентами используется протокол MQTT, что позволяет передавать изображение экрана и команды управления в реальном времени.

## Возможности

- **Демонстрация экрана**: передача рабочего стола удаленным клиентам в реальном времени
- **Удаленное управление**: управление мышью и клавиатурой удаленного компьютера
- **Поддержка нескольких клиентов**: одновременное подключение нескольких клиентов к одному серверу
- **Безопасная коммуникация**: использование MQTT с аутентификацией
- **Синхронизация курсора**: передача позиции и типа курсора в реальном времени
- **Управление клавиатурой**: поддержка обычных и специальных клавиш
- **Управление мышью**: перемещение, клики, прокрутка, перетаскивание
- **Адресная книга**: сохранение и управление частыми подключениями
- **Управление настройками**: параметры сервера, пароля и MQTT

## Архитектура

Приложение состоит из двух основных компонентов:

1. **Сервер (`ScreenShareServer`)**: захватывает экран, отправляет кадры клиентам и обрабатывает команды удаленного управления.
2. **Клиент (`ScreenShareClient`)**: подключается к серверу, отображает экран и отправляет события мыши/клавиатуры.

### Протокол обмена

Для взаимодействия используется MQTT (Message Queuing Telemetry Transport).

- **Топики сервера**:
  - `server/status`: изменения состояния сервера
  - `server/size`: запрос размера экрана
  - `server/update/first`: первый кадр
  - `server/update/next`: последующие кадры
  - `server/keyboard/keypress`: нажатия клавиш
  - `server/mouse/*`: события мыши (позиция, клики, движение, колесо)

- **Топики клиента**:
  - `client/status`: изменения состояния клиента
  - `client/size`: информация о размере экрана
  - `client/update/first`: первый кадр
  - `client/update/next`: последующие кадры
  - `client/mouse/position`: обновления позиции курсора

## Установка

### Требования

- Python 3.8 и выше
- Windows (используются API Win32)
- MQTT-брокер (например, Mosquitto, HiveMQ)

### Необходимые библиотеки

```bash
pip install PyQt6 opencv-python paho-mqtt pyautogui pyperclip mss pynput numpy
```

### Настройка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/yourusername/pyStudyFlash.git
cd pyStudyFlash
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Настройте MQTT в `sets/settings.ini`:

```ini
[General]
server_address=your_email@example.com
server_password=your_password
mqtt_address=your_mqtt_broker_address
mqtt_port=1883
mqtt_timeout=60
mqtt_username=
mqtt_password=
mqtt_transport=tcp
mqtt_use_tls=false
mqtt_tls_insecure=false
mqtt_ws_path=/mqtt
```

### Установка MQTT брокера (Mosquitto)

Вариант 1: Windows

1. Скачайте Mosquitto с официального сайта: `https://mosquitto.org/download/`.
2. Установите как Windows Service (службу).
3. Проверьте, что служба запущена:

```powershell
Get-Service mosquitto
```

Вариант 2: Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
sudo systemctl status mosquitto
```

### Добавление пользователя и пароля

Windows (пример пути установки):

```powershell
New-Item -Path "C:\mosquitto" -ItemType Directory -Force
& "C:\Program Files\mosquitto\mosquitto_passwd.exe" -c "C:\mosquitto\passwd" pyflash
# Важно для службы: дайте SYSTEM право чтения файла паролей
icacls "C:\mosquitto\passwd" /inheritance:e
icacls "C:\mosquitto\passwd" /grant "SYSTEM:(R)"
```

Linux:

```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd pyflash
```

### Базовый безопасный `mosquitto.conf`

Минимум для локальной сети (TCP, логин/пароль), Linux:

```conf
per_listener_settings true

listener 1883 0.0.0.0
protocol mqtt
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Минимум для локальной сети (TCP, логин/пароль), Windows:

```conf
per_listener_settings true

listener 1883 0.0.0.0
protocol mqtt
allow_anonymous false
password_file C:\mosquitto\passwd
```

Перезапуск брокера после изменений:

Windows:

```powershell
Restart-Service mosquitto
```

Linux:

```bash
sudo systemctl restart mosquitto
```

### Доступ из интернета: что нужно сделать

1. Дайте ПК с брокером постоянный локальный IP (DHCP reservation), например `192.168.0.66`.
2. Настройте проброс портов на роутере (NAT/PAT):
   - Рекомендуется: внешний `8883` -> `192.168.0.66:8883` (MQTT over TLS).
   - Опционально: внешний `443` -> `192.168.0.66:443` (MQTT over WSS/WebSockets TLS).
   - Не рекомендуется открывать наружу `1883` без TLS.
3. Откройте входящие порты в firewall ОС.
4. Используйте внешний IP или DDNS-домен в `mqtt_address`.
5. Если CG-NAT у провайдера, проброс портов может не работать; тогда нужен VPS/VPN/reverse tunnel.

#### Какие порты пробрасывать

| Сценарий | Внешний порт | Внутренний адрес:порт | Протокол | Рекомендация |
|---|---:|---|---|---|
| MQTT TCP без TLS (только LAN/тест) | 1883 | `192.168.0.66:1883` | TCP | Не открывать в интернет |
| MQTT TCP + TLS | 8883 | `192.168.0.66:8883` | TCP | Основной вариант для интернета |
| MQTT over WebSockets + TLS | 443 | `192.168.0.66:443` | TCP | Удобно, если 8883 блокируется |

#### Открытие портов в firewall

Windows (PowerShell от администратора):

```powershell
New-NetFirewallRule -DisplayName "MQTT TLS 8883" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8883
New-NetFirewallRule -DisplayName "MQTT WSS 443" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 443
```

Ubuntu/Debian (UFW):

```bash
sudo ufw allow 8883/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

#### Проверка, что брокер доступен из интернета

Из внешней сети (не из той же LAN) проверьте порт:

```powershell
Test-NetConnection your-ddns-name.example.org -Port 8883
```

Проверьте подключение MQTT клиентом:

```bash
mosquitto_sub -h your-ddns-name.example.org -p 8883 -u pyflash -P "strong_password" -t "test/topic" --cafile ca.crt
```

### Конфиг для интернета (рекомендуется TLS)

Пример MQTT over TLS:

```conf
per_listener_settings true

listener 8883 0.0.0.0
protocol mqtt
allow_anonymous false
password_file /etc/mosquitto/passwd

cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
```

Пример MQTT over WebSockets TLS:

```conf
per_listener_settings true

listener 443 0.0.0.0
protocol websockets
allow_anonymous false
password_file /etc/mosquitto/passwd

cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
```

### Подробно про параметры `settings.ini`

`server_address`

- Идентификатор сервера в вашем приложении (используется в префиксе топиков).
- Должен совпадать у сервера и клиентов для одной сессии.

`server_password`

- Часть topic-prefix в приложении.
- Это не пароль MQTT брокера.
- Должен совпадать у сервера и клиентов.

`mqtt_address`

- Адрес MQTT брокера: домен или IP.
- Для интернета указывайте внешний IP или DDNS-имя.

`mqtt_port`

- Типовые значения:
  - `1883` - MQTT TCP без TLS.
  - `8883` - MQTT TCP с TLS.
  - `8080/8083` - MQTT over WebSockets.
  - `443` - MQTT over WSS (рекомендуется для интернета).

`mqtt_timeout`

- Таймаут подключения в секундах.
- Обычно `60`.

`mqtt_username` / `mqtt_password`

- Учетные данные пользователя брокера (из `mosquitto_passwd`).
- Если брокер требует авторизацию, поля обязательны.

`mqtt_transport`

- `tcp` для классического MQTT.
- `websockets` для MQTT over WS/WSS.

`mqtt_use_tls`

- `true` включает TLS.
- Для интернета рекомендуется `true`.

`mqtt_tls_insecure`

- `true` отключает строгую проверку сертификата.
- Используйте только для теста.
- Для продакшена должно быть `false`.

`mqtt_ws_path`

- Путь для WebSockets подключения.
- Обычно `/mqtt`, но зависит от конфигурации брокера/прокси.

### Примеры `settings.ini`

Локальная сеть, TCP без TLS:

```ini
[General]
server_address=teacher@example.com
server_password=group1
mqtt_address=192.168.0.66
mqtt_port=1883
mqtt_timeout=60
mqtt_username=pyflash
mqtt_password=strong_password
mqtt_transport=tcp
mqtt_use_tls=false
mqtt_tls_insecure=false
mqtt_ws_path=/mqtt
```

Интернет, TCP + TLS:

```ini
[General]
server_address=teacher@example.com
server_password=group1
mqtt_address=your-ddns-name.example.org
mqtt_port=8883
mqtt_timeout=60
mqtt_username=pyflash
mqtt_password=strong_password
mqtt_transport=tcp
mqtt_use_tls=true
mqtt_tls_insecure=false
mqtt_ws_path=/mqtt
```

Интернет, WebSockets + TLS:

```ini
[General]
server_address=teacher@example.com
server_password=group1
mqtt_address=your-ddns-name.example.org
mqtt_port=443
mqtt_timeout=60
mqtt_username=pyflash
mqtt_password=strong_password
mqtt_transport=websockets
mqtt_use_tls=true
mqtt_tls_insecure=false
mqtt_ws_path=/mqtt
```

### Проверка подключения

В приложении:

1. Откройте `Меню -> Настройки -> MQTT`.
2. Нажмите `Проверить MQTT подключение`.
3. После успешного теста нажмите `Сохранить`.

## Использование

### Запуск в режиме сервера

1. Запустите приложение:

```bash
python pystudyflash.py
```

2. Нажмите **"Старт доступ"**, чтобы начать трансляцию экрана.

### Подключение в режиме клиента

1. Запустите приложение:

```bash
python pystudyflash.py
```

2. Введите адрес сервера в поле ввода.
3. Нажмите **"Подключиться"**.

### Конфигурация

- **Настройки**: меню (`☰`) -> **"Настройки"**
- **Адресная книга**: меню (`☰`) -> **"Адресная книга"**

## Безопасность

- Доступ к серверу по паролю
- Аутентификация MQTT
- Шифрование при использовании MQTT-брокера с TLS

## Структура проекта

```text
pyStudyFlash/
|-- pystudyflash.py     # Точка входа приложения
|-- server.py           # Логика сервера демонстрации экрана
|-- client.py           # Логика клиента
|-- cursor.py           # Работа с курсором
|-- classes/            # Вспомогательные классы
|   |-- get_cursor.py   # Определение системного курсора
|   `-- timer_server.py # Таймер
|-- cursors/            # PNG-изображения курсоров
|-- sets/               # Файлы конфигурации
|-- util/               # Вспомогательные скрипты
`-- docs/               # Документация
```

## Технические детали

### Захват и передача экрана

1. Сервер захватывает экран через `mss`.
2. Кадры сжимаются (`zlib`) и кодируются (`base64`).
3. Для снижения трафика используется передача различий между кадрами (XOR).
4. Данные отправляются через MQTT.

### Удаленное управление

1. Клиент отправляет события мыши на сервер.
2. Сервер принимает и эмулирует клавиатуру/мышь.
3. Поддерживается синхронизация курсора.
4. Обрабатываются сочетания специальных клавиш (Ctrl, Alt, Shift и т.д.).

### Интерфейс

- Графический интерфейс на PyQt6
- MDI (несколько окон клиентов одновременно)
- Панель инструментов управления подключениями
- Диалог настроек
- Адресная книга

## Вклад в проект

1. Сделайте fork репозитория.
2. Создайте ветку для изменений.
3. Закоммитьте изменения.
4. Отправьте ветку в удаленный репозиторий.
5. Создайте Pull Request.

## Лицензия

Проект распространяется по лицензии MIT. Подробности в файле `LICENSE`.

## Автор

pyStudyFlash разработан как решение для демонстрации экрана и удаленного управления в образовательных и совместных сценариях работы.

## Сборка установочных пакетов для Windows

В репозитории добавлены скрипты для сборки дистрибутива и установщика.

### 1. Сборка дистрибутива (PyInstaller)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_dist.ps1
```

Результат:

- `dist\pyStudyFlash\pyStudyFlash.exe`

### 2. Сборка `Setup.exe` (Inno Setup)

Сначала установите **Inno Setup 6**, 

На Windows проще всего так:


Скачайте установщик с официального сайта: https://jrsoftware.org/isdl.php
Запустите .exe и установите с настройками по умолчанию (Next -> Install).
Проверьте, что появился компилятор ISCC.exe:
обычно: C:\Program Files (x86)\Inno Setup 6\ISCC.exe
или: C:\Program Files\Inno Setup 6\ISCC.exe
Проверка в PowerShell:

& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /?
После этого в вашем проекте можно запускать:

powershell -ExecutionPolicy Bypass -File .\scripts\build_setup.ps1 -AppVersion 1.0.0
Если путь нестандартный, передайте его явно:

powershell -ExecutionPolicy Bypass -File .\scripts\build_setup.ps1 -AppVersion 1.0.0 -IsccPath "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

Результат:

- `installer\output\pyStudyFlash-setup-1.0.0.exe` (версия зависит от `-AppVersion`)

### Сборка одной командой

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_all.ps1 -AppVersion 1.0.0
```

### Где хранятся данные установленного приложения

В установленной версии записываемые файлы находятся в:

- `%APPDATA%\pyStudyFlash\settings.ini`
- `%APPDATA%\pyStudyFlash\address_book`

## Настройка MQTT через интерфейс (работа через интернет)

Начиная с текущей версии MQTT можно полностью настроить из интерфейса программы:

1. Откройте `Меню -> Настройки -> MQTT`.
2. Заполните параметры подключения:
   - `Адрес` - домен или IP MQTT брокера.
   - `Порт` - например `1883`, `8883`, `8080`, `8083` или `443`.
   - `Таймаут` - обычно `60`.
   - `Транспорт`:
     - `TCP` для обычного MQTT.
     - `WebSockets` для MQTT over WS/WSS.
   - `Пользователь` / `Пароль` - если брокер требует авторизацию.
   - `Использовать TLS` - включайте для безопасного подключения через интернет.
   - `Разрешить недоверенный сертификат` - только для тестовой среды.
   - `WebSocket path` - обычно `/mqtt` (зависит от брокера).
3. Нажмите `Проверить MQTT подключение`.
4. Нажмите `Сохранить`.

Эти параметры используются:

- при запуске локального сервера (`Старт доступ`);
- при подключении клиента (`Подключиться`);
- при открытии окна просмотра клиента из серверного окна.

### Адресная книга и MQTT

В записях адресной книги теперь можно хранить не только `MQTT сервер/порт/таймаут`, но и:

- `MQTT пользователь`
- `MQTT пароль`
- `MQTT транспорт` (`tcp` или `websockets`)
- `MQTT TLS` (`true/false`)
- `MQTT TLS insecure` (`true/false`)
- `MQTT WS path`

Логика применения:

- если поле в записи заполнено — используется значение из записи;
- если поле пустое (`Из настроек`) — используется значение из `Меню -> Настройки -> MQTT`.

### Примеры интернет-настроек

- MQTT + TLS:
  - Транспорт: `TCP`
  - Порт: `8883`
  - TLS: `включен`
- MQTT over WSS:
  - Транспорт: `WebSockets`
  - Порт: `443`
  - TLS: `включен`
  - WebSocket path: чаще всего `/mqtt`

## Подробная сборка установщика

Подробная инструкция на русском: [docs/BUILD_INSTALLER_RU.md](docs/BUILD_INSTALLER_RU.md).
