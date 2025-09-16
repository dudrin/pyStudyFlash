# Project Structure

## Overview

pyStudyFlash is a screen sharing application built with PyQt6 that allows users to share their desktop screen and remotely control other computers. The application uses MQTT protocol for communication between server and client components.

## Directory Structure

```
pyStudyFlash/
├── classes/                 # Utility classes
│   ├── get_cursor.py       # System cursor detection functionality
│   └── timer_server.py     # Timer implementation for server operations
├── cursors/                # PNG images for different mouse cursor types
├── docs/                   # Documentation files
├── output/                 # Output directory (excluded in .gitignore)
├── sets/                   # Configuration files
│   └── settings.ini        # Application settings (excluded in .gitignore)
├── util/                   # Utility scripts and development versions
└── venv/                   # Virtual environment (excluded in .gitignore)
```

## Main Components

### Core Files

1. **pystudyflash.py** - Main application entry point
   - Contains the main GUI application class [ScreenShareApp](file:///F:/QT6/pyStudyFlash/pystudyflash.py#L135-L403)
   - Implements the main window with toolbar, menu, and MDI area
   - Manages server and client connections
   - Handles settings and address book functionality

2. **server.py** - Screen sharing server implementation
   - Captures screen using MSS library
   - Encodes and transmits screen frames via MQTT
   - Processes remote control commands from clients
   - Handles mouse and keyboard input simulation

3. **client.py** - Screen sharing client implementation
   - Connects to server via MQTT
   - Receives and displays screen frames
   - Captures user input and sends to server
   - Handles cursor rendering and synchronization

4. **cursor.py** - Mouse cursor handling
   - Loads cursor images from the cursors directory
   - Draws cursor on shared screen images
   - Supports multiple cursor types (arrow, hand, wait, etc.)

### Configuration Files

1. **sets/settings.ini** - Application settings
   - Server address and password
   - MQTT broker configuration
   - Connection parameters

2. **sets/address_book** - Saved server connections (binary file)
   - Stores frequently used server addresses
   - Saves connection credentials and settings

### Documentation Files

1. **README.md** - Project overview and usage instructions
2. **LICENSE** - MIT license terms
3. **requirements.txt** - Python package dependencies
4. **setup.py** - Package installation configuration
5. **.gitignore** - Files and directories to exclude from Git

## Key Classes

### ScreenShareApp (pystudyflash.py)
Main application window that manages:
- Server and client connections
- Settings dialog
- Address book management
- MDI area for multiple client windows

### ScreenShareServer (server.py)
Server component that:
- Captures screen content
- Encodes frames for transmission
- Processes remote control commands
- Manages MQTT communication

### ScreenShareClient (client.py)
Client component that:
- Connects to servers
- Displays shared screens
- Captures and sends user input
- Handles cursor synchronization

### SettingsDialog (pystudyflash.py)
Configuration interface for:
- Server address and password
- MQTT broker settings
- Connection timeout parameters

### AddressBookDialog (pystudyflash.py)
Connection management for:
- Storing server connection details
- Organizing connections in groups
- Quick access to frequently used servers

## Communication Flow

1. **Server Initialization**
   - Server starts and connects to MQTT broker
   - Waits for client connections

2. **Client Connection**
   - Client connects to MQTT broker
   - Requests screen size information
   - Subscribes to screen update topics

3. **Screen Sharing**
   - Server captures screen frames
   - Encodes frames using XOR compression
   - Publishes frames to MQTT topics
   - Client receives and displays frames

4. **Remote Control**
   - Client captures mouse/keyboard input
   - Sends input events to server via MQTT
   - Server processes events using pyautogui
   - Server publishes cursor updates to client

## Data Flow

### Screen Transmission
```
Server Screen Capture → MSS → Image Processing → XOR Compression → Base64 Encoding → MQTT Publish → Client Receive → Base64 Decoding → XOR Decompression → Image Display
```

### Input Transmission
```
Client Input Capture → Event Packaging → MQTT Publish → Server Receive → Event Processing → System Input Simulation
```

## Security Considerations

1. **Authentication**
   - Server password protection
   - MQTT broker authentication

2. **Data Protection**
   - Password fields are masked in UI
   - Configuration files are excluded from repository
   - XOR encoding for screen frame compression

3. **Access Control**
   - Only authorized clients can connect
   - Server controls which clients have control access