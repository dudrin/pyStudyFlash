# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-09-16

### Added
- Initial release of pyStudyFlash
- Screen sharing functionality using PyQt6 and MQTT
- Remote desktop control capabilities
- Server and client implementation
- Address book for connection management
- Settings dialog for configuration
- Multi-client support through MDI interface
- Mouse cursor synchronization
- Keyboard input handling
- Password-protected server access
- MQTT-based communication protocol
- Documentation including README, usage guide, and project structure
- Installation requirements and setup files
- Git ignore configuration
- License information

### Features
- Real-time screen sharing with frame compression
- Remote mouse and keyboard control
- Support for special keys and key combinations
- Multiple cursor type visualization
- Connection management through address book
- Configurable MQTT settings
- Cross-platform compatibility (Windows)
- Secure communication through MQTT authentication

### Technical Details
- Built with PyQt6 for graphical interface
- Uses MSS library for screen capture
- Implements XOR encoding for efficient frame transmission
- Leverages paho-mqtt for MQTT communication
- Utilizes pyautogui for input simulation
- Employs pynput for input capture
- Integrates OpenCV for image processing
- Win32 API integration for cursor detection