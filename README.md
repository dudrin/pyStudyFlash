# pyStudyFlash

pyStudyFlash is a PyQt6-based screen sharing application that allows remote control and viewing of computer screens. The application uses MQTT protocol for communication between server and client components, enabling real-time screen sharing and remote desktop control.

## Features

- **Screen Sharing**: Share your desktop screen with remote clients in real-time
- **Remote Control**: Allow remote users to control your mouse and keyboard
- **Multi-client Support**: Support multiple clients connecting to the same server
- **Secure Communication**: Uses MQTT protocol with authentication for secure communication
- **Cursor Synchronization**: Real-time cursor position and type synchronization
- **Keyboard Control**: Remote keyboard input support with special key handling
- **Mouse Control**: Full mouse control including clicks, movement, and scrolling
- **Address Book**: Save and manage frequently used server connections
- **Settings Management**: Configure server addresses, passwords, and MQTT settings

## Architecture

The application consists of two main components:

1. **Server (ScreenShareServer)**: Captures the screen and shares it with connected clients. It also receives and processes remote control commands from clients.

2. **Client (ScreenShareClient)**: Connects to a server, displays the shared screen, and sends user input (mouse/keyboard) back to the server.

### Communication Protocol

The application uses MQTT (Message Queuing Telemetry Transport) protocol for communication between server and client:

- **Server Topics**:
  - `server/status`: Server status updates
  - `server/size`: Screen size requests
  - `server/update/first`: First screen frame
  - `server/update/next`: Subsequent screen frames
  - `server/keyboard/keypress`: Keyboard input
  - `server/mouse/*`: Mouse events (position, clicks, movement, wheel)

- **Client Topics**:
  - `client/status`: Client status updates
  - `client/size`: Screen size information
  - `client/update/first`: First screen frame
  - `client/update/next`: Subsequent screen frames
  - `client/mouse/position`: Mouse position updates

## Installation

### Prerequisites

- Python 3.8 or higher
- Windows OS (due to win32 API usage)
- MQTT Broker (e.g., Mosquitto, HiveMQ)

### Required Libraries

```bash
pip install PyQt6 opencv-python paho-mqtt pyautogui pyperclip mss pynput numpy
```

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pyStudyFlash.git
cd pyStudyFlash
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure MQTT settings in `sets/settings.ini`:
```ini
[General]
server_address=your_email@example.com
server_password=your_password
mqtt_address=your_mqtt_broker_address
mqtt_port=1883
mqtt_timeout=60
```

## Usage

### Starting the Server

1. Run the main application:
```bash
python pystudyflash.py
```

2. Click "Старт доступ" (Start Access) to begin sharing your screen

### Connecting as a Client

1. Run the main application:
```bash
python pystudyflash.py
```

2. Enter the server address in the input field
3. Click "Подключиться" (Connect) to connect to the server

### Configuration

- **Settings**: Access through the menu (☰) → "Настройки" (Settings)
- **Address Book**: Save and manage server connections through "Адресная книга" (Address Book)

## Security

- Password-protected server access
- MQTT authentication
- Encrypted communication (when using TLS-enabled MQTT brokers)

## Project Structure

```
pyStudyFlash/
├── pystudyflash.py     # Main application entry point
├── server.py           # Screen sharing server implementation
├── client.py           # Screen sharing client implementation
├── cursor.py           # Mouse cursor handling
├── classes/            # Utility classes
│   ├── get_cursor.py   # System cursor detection
│   └── timer_server.py # Timer implementation
├── cursors/            # Cursor image files
├── sets/               # Configuration files
├── util/               # Utility scripts
└── docs/               # Documentation files
```

## Technical Details

### Screen Capture and Transmission

1. The server captures the screen using `mss` library
2. Images are compressed using zlib and base64 encoded
3. Frame differencing is used to reduce bandwidth (XOR encoding)
4. Images are transmitted via MQTT messages

### Remote Control

1. Mouse events are captured on the client and sent to the server
2. Keyboard events are processed and simulated on the server
3. Cursor position synchronization between client and server
4. Special key combinations handling (Ctrl, Alt, Shift)

### UI Components

- PyQt6 for the graphical interface
- MDI (Multiple Document Interface) for multiple client windows
- Toolbar with connection controls
- Settings dialog for configuration
- Address book for connection management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

pyStudyFlash was developed as a screen sharing and remote control solution for educational and collaborative purposes.