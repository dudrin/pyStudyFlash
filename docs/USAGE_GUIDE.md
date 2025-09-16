# Usage Guide

## Getting Started

### Prerequisites

1. **Python 3.8 or higher** installed on your system
2. **Windows OS** (due to win32 API dependencies)
3. **MQTT Broker** (can be local or remote)

### Installation

1. Clone or download the repository
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Before using the application, configure your MQTT settings:

1. Open the application
2. Click the menu button (☰) in the toolbar
3. Select "Настройки" (Settings)
4. Configure the following:
   - **Server Address**: Your email or identifier
   - **Server Password**: Password for server access
   - **MQTT Server**: Address of your MQTT broker
   - **MQTT Port**: Port number (default: 1883)
   - **MQTT Timeout**: Connection timeout in seconds

## Using as a Server (Sharing Your Screen)

1. Launch the application:
   ```bash
   python pystudyflash.py
   ```

2. Click the "Старт доступ" (Start Access) button in the main window
3. Your screen is now being shared and can be accessed by clients

### Server Features

- **Multiple Client Support**: Multiple clients can connect to your shared screen
- **Remote Control**: Allow connected clients to control your mouse and keyboard
- **Access Control**: Password-protected access to your shared screen
- **Real-time Updates**: Screen updates are transmitted in real-time

## Using as a Client (Viewing a Shared Screen)

1. Launch the application:
   ```bash
   python pystudyflash.py
   ```

2. Enter the server address in the input field at the top
3. Click "Подключиться" (Connect) to establish connection
4. The shared screen will appear in a new window

### Client Features

- **Screen Viewing**: View the shared screen in real-time
- **Remote Control**: Control the server's mouse and keyboard (if permitted)
- **Multiple Connections**: Connect to multiple servers simultaneously
- **Address Book**: Save frequently used server addresses for quick access

## Managing Connections

### Address Book

1. Click the menu button (☰) in the toolbar
2. Select "Адресная книга" (Address Book)
3. Use the following options:
   - **Добавить** (Add): Add a new server connection
   - **Редактировать** (Edit): Modify existing connection details
   - **Удалить** (Delete): Remove a connection
   - **Просмотр** (View): Connect to selected server
   - **Просмотр группы** (View Group): Connect to all servers in the same group

### Connection Fields

When adding or editing a connection, you can specify:
- **Адрес сервера** (Server Address): Email or identifier of the server
- **Пользователь** (User): Username for the connection
- **Пароль** (Password): Password for server access
- **Группа** (Group): Group name for organizing connections
- **MQTT сервер** (MQTT Server): MQTT broker address
- **MQTT порт** (MQTT Port): MQTT broker port
- **MQTT таймаут** (MQTT Timeout): Connection timeout

## Remote Control Features

### Mouse Control

- **Movement**: Move your mouse to control the server's cursor
- **Left Click**: Perform left mouse clicks on the server
- **Right Click**: Perform right mouse clicks on the server
- **Scrolling**: Use mouse wheel to scroll on the server
- **Dragging**: Hold left mouse button to drag items

### Keyboard Control

- **Text Input**: Type text that appears on the server
- **Special Keys**: Use Ctrl, Alt, Shift combinations
- **Function Keys**: F1-F12 and other special keys
- **Navigation**: Arrow keys, Enter, Tab, etc.

## Troubleshooting

### Common Issues

1. **Cannot Connect to Server**
   - Check MQTT broker address and port
   - Verify server is running and accessible
   - Confirm server password is correct

2. **Poor Screen Quality**
   - Check network connection quality
   - Reduce screen update frequency in code
   - Ensure sufficient bandwidth

3. **Mouse Cursor Not Visible**
   - Verify cursor image files are present in cursors/ directory
   - Check that cursor.png files are not corrupted

4. **Keyboard Input Not Working**
   - Ensure server has granted control permissions
   - Check that no other applications are capturing input

### Logs and Debugging

The application outputs debug information to the console, including:
- Connection status
- MQTT message exchanges
- Error messages
- Client/server events

## Advanced Configuration

### Custom MQTT Broker

You can use various MQTT brokers:
- **Mosquitto**: Local MQTT broker
- **HiveMQ**: Cloud-based MQTT service
- **AWS IoT**: Amazon's MQTT service
- **Google Cloud IoT**: Google's MQTT service

### Performance Tuning

Adjust the following parameters in the source code for better performance:
- **Update Interval**: Timer interval in [ScreenShareServer](file:///F:/QT6/pyStudyFlash/server.py#L15-L294) and [ScreenShareClient](file:///F:/QT6/pyStudyFlash/client.py#L13-L304)
- **Compression Level**: ZLIB compression level in screen encoding
- **Frame Skipping**: Implement frame skipping for lower bandwidth

## Security Best Practices

1. **Use Strong Passwords**: Always use strong, unique passwords for server access
2. **Secure MQTT Broker**: Use authenticated and encrypted MQTT connections
3. **Network Security**: Run the application on secure networks
4. **Access Control**: Only grant control permissions to trusted users
5. **Regular Updates**: Keep the application and dependencies updated

## FAQ

### Can I use this on Linux or macOS?

The application is designed for Windows due to win32 API dependencies. However, with modifications to the cursor handling and system integration code, it could potentially work on other platforms.

### How many clients can connect simultaneously?

The application can theoretically support multiple clients, but performance depends on:
- Server hardware capabilities
- Network bandwidth
- MQTT broker limitations
- Screen resolution and update frequency

### Is the connection encrypted?

The application uses standard MQTT protocol. For encryption, configure your MQTT broker to use TLS/SSL encryption.

### Can I share only specific applications instead of the entire screen?

The current implementation shares the entire screen. To share specific applications, modifications would be needed to capture only specific windows.

## Support

For issues, questions, or contributions, please:
1. Check the documentation
2. Review existing issues in the repository
3. Create a new issue with detailed information
4. Submit a pull request for improvements