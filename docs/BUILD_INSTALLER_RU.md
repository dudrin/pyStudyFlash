# Сборка установщика pyStudyFlash для Windows

Этот документ описывает, как собрать запускаемый `.exe`-установщик pyStudyFlash.

В проекте есть два разных варианта установщика:

- `pyStudyFlash-setup-X.Y.Z.exe` - автономный установщик. Он содержит собранное приложение, Python runtime и нужные библиотеки. На компьютере пользователя не нужно отдельно ставить Python и пакеты.
- `pyStudyFlash-source-setup-X.Y.Z.exe` - исходный установщик. Он маленький, потому что кладет исходники и при установке создает `.venv`, затем ставит пакеты. Для конечного пользователя этот вариант хуже: ему нужен Python и доступ к пакетам.

Если нужен установщик, который можно перенести на другой компьютер и запустить без ручной настройки окружения, собирайте автономный вариант `pyStudyFlash-setup-X.Y.Z.exe`.

## Что должно быть установлено на компьютере сборки

Сборка выполняется на Windows.

Нужно установить:

- Python 3.8 или новее. Текущая сборка проверялась с Python 3.11.
- Inno Setup 6: https://jrsoftware.org/isdl.php
- Доступ в интернет для первой установки зависимостей сборки.

Обычно Inno Setup устанавливается сюда:

```powershell
C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

## Быстрая сборка автономного установщика

Откройте PowerShell в корне проекта, например:

```powershell
cd F:\QT6\pyStudyFlash
```

Разрешите запуск скриптов только для текущего окна PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Создайте виртуальное окружение, если его еще нет:

```powershell
py -3 -m venv venv
```

Активируйте окружение:

```powershell
.\venv\Scripts\Activate.ps1
```

Обновите `pip`:

```powershell
python -m pip install --upgrade pip
```

Соберите приложение и установщик одной командой:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_all.ps1 -PythonExe .\venv\Scripts\python.exe -AppVersion 1.0.4
```

Номер версии можно заменить на нужный, например `1.0.5`.

После успешной сборки появятся:

```text
dist\pyStudyFlash\pyStudyFlash.exe
installer\output\pyStudyFlash-setup-1.0.4.exe
```

Файл `installer\output\pyStudyFlash-setup-1.0.4.exe` - это готовый автономный установщик.

## Что именно делает сборка

Скрипт `scripts\build_all.ps1` запускает два этапа:

1. `scripts\build_dist.ps1`

   Этот этап ставит зависимости из `requirements.txt` и `requirements-build.txt`, затем запускает PyInstaller по файлу `pyinstaller.spec`.

   Результат этапа:

   ```text
   dist\pyStudyFlash\pyStudyFlash.exe
   dist\pyStudyFlash\_internal\...
   ```

   В папке `_internal` лежат Python runtime и библиотеки приложения: PyQt6, numpy, OpenCV, win32-модули и другие зависимости.

2. `scripts\build_setup.ps1`

   Этот этап запускает Inno Setup и упаковывает всю папку `dist\pyStudyFlash` в один установщик.

   Результат этапа:

   ```text
   installer\output\pyStudyFlash-setup-X.Y.Z.exe
   ```

## Как проверить, что установщик автономный

После сборки проверьте, что внутри `dist` есть Python runtime:

```powershell
Test-Path .\dist\pyStudyFlash\_internal\python311.dll
```

Если команда вернула `True`, Python runtime включен в сборку.

Также можно посмотреть основные файлы:

```powershell
Get-ChildItem .\dist\pyStudyFlash\_internal | Select-Object Name
```

В списке должны быть папки и файлы библиотек, например `PyQt6`, `cv2`, `numpy`, `python311.dll`, `VCRUNTIME140.dll`.

Перед упаковкой установщика можно запустить собранное приложение напрямую:

```powershell
.\dist\pyStudyFlash\pyStudyFlash.exe
```

Если окно приложения открывается из `dist`, установщик будет устанавливать именно эту собранную версию.

## Сборка по этапам

Если нужно отдельно собрать только папку приложения:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_dist.ps1 -PythonExe .\venv\Scripts\python.exe
```

Если папка `dist\pyStudyFlash` уже собрана и нужно только пересобрать установщик:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_setup.ps1 -AppVersion 1.0.4
```

Если Inno Setup установлен не в стандартную папку, передайте путь к `ISCC.exe` явно:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_setup.ps1 -AppVersion 1.0.4 -IsccPath "C:\Tools\Inno Setup 6\ISCC.exe"
```

## Исходный установщик

Исходный установщик собирается отдельным скриптом:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_source_setup.ps1 -AppVersion 1.0.4
```

Результат:

```text
installer\output\pyStudyFlash-source-setup-1.0.4.exe
```

Этот файл заметно меньше автономного установщика, потому что не содержит полный Python runtime и все установленные библиотеки. При установке он создает окружение и ставит пакеты. Для распространения без дополнительных требований лучше использовать автономный `pyStudyFlash-setup-X.Y.Z.exe`.

## Что не попадает в Git

Папки сборки не нужно коммитить:

```text
build\
dist\
installer\output\
venv\
```

Они исключены через `.gitignore`. В Git хранятся исходники, скрипты сборки и настройки упаковки. Готовый `.exe`-установщик нужно хранить локально или прикладывать к GitHub Release отдельно.

## Частые проблемы

### Inno Setup не найден

Ошибка:

```text
ISCC.exe not found. Install Inno Setup 6 or pass -IsccPath.
```

Решение:

- установите Inno Setup 6;
- или передайте путь к `ISCC.exe` через параметр `-IsccPath`.

### Ошибка сертификата при установке пакетов pip

Скрипт `scripts\build_dist.ps1` уже очищает переменные `PIP_CERT`, `REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, `CURL_CA_BUNDLE`, потому что в некоторых системах они указывают на несуществующие сертификаты.

Если запускаете команды вручную и снова видите ошибку сертификата, очистите переменные в текущем PowerShell:

```powershell
Remove-Item Env:PIP_CERT -ErrorAction SilentlyContinue
Remove-Item Env:REQUESTS_CA_BUNDLE -ErrorAction SilentlyContinue
Remove-Item Env:SSL_CERT_FILE -ErrorAction SilentlyContinue
Remove-Item Env:CURL_CA_BUNDLE -ErrorAction SilentlyContinue
```

### После установки окно не открывается

Сначала проверьте запуск из папки `dist`:

```powershell
.\dist\pyStudyFlash\pyStudyFlash.exe
```

Если из `dist` приложение не запускается, проблема не в Inno Setup, а в PyInstaller-сборке. Нужно проверить `pyinstaller.spec`: возможно, не добавлен скрытый импорт или файл данных.

Если из `dist` приложение запускается, но установленная версия нет, проверьте путь установки и права доступа. Автономный установщик ставит приложение в:

```text
C:\Program Files\pyStudyFlash
```

или в соответствующую папку `Program Files` для текущей архитектуры Windows.

### Антивирус предупреждает о файле

PyInstaller-приложения иногда вызывают предупреждения, потому что внутри одного `.exe` находится загрузчик и Python-приложение. Для распространения пользователям лучше подписать установщик цифровой подписью.

## Настройки установленной программы

Настройки и пользовательские файлы приложения хранятся не в папке установки, а в профиле пользователя:

```text
%APPDATA%\pyStudyFlash
```

Это позволяет обновлять программу без потери настроек.
