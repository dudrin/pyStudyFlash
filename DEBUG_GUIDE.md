# Debug Guide for pyStudyFlash Connection Issue

## Current Status
- Client connects to MQTT ✓
- Client sends registration message ✓ 
- Server receives message but doesn't process it ❌

## Enhanced Debug Steps

### 1. First, test MQTT message flow
```bash
python test_mqtt_flow.py
```
This will verify if MQTT messages are being delivered properly.

### 2. Start server with enhanced debugging
```bash
python pystudyflash.py
```
- Click "Старт доступ" (Start Access)  
- Look for these debug messages:

**Expected output:**
```
=== SERVER SUBSCRIPTIONS ===
Topic prefix: 'dudkate@yandex.ru/123456'
Subscribed to: 'dudkate@yandex.ru/123456/server/status' -> (0, 1)
...
=== END SUBSCRIPTIONS ===
```

**When client connects, you should see:**
```
>>> SERVER RECEIVED MESSAGE <<<
Topic: dudkate@yandex.ru/123456/server/status
Expected topic: dudkate@yandex.ru/123456/server/status
Topic matches: True
Payload: register|<client_id>|DESKTOP-I2KE1NN
<<< END MESSAGE <<<

>>> _HANDLE_MESSAGE CALLED <<<
SUCCESS: Processing server/status message
SUCCESS: Client registration request: register|<client_id>|DESKTOP-I2KE1NN
```

### 3. Start client
```bash
python pystudyflash.py
```
- Leave address field EMPTY
- Click "Подключиться" (Connect)

### 4. Check debug output

**If you DON'T see server receiving messages:**
- MQTT broker issue or firewall blocking
- Topic prefix mismatch (should be identical)
- Server not subscribed to correct topics

**If server receives but doesn't process:**
- Look for errors in `_handle_message`
- Check if topic comparison is working

**If everything looks correct but still not working:**
- Check if `register_client()` method is being called
- Verify client registration is completing

## Troubleshooting

### Issue: Server doesn't receive any messages
```bash
# Check MQTT connectivity
python test_mqtt_flow.py
```

### Issue: Server receives but topic doesn't match
Check that both client and server use exact same topic prefix:
```bash
python verify_config.py
```

### Issue: Server processes registration but client doesn't get response
Check if server is publishing responses on correct topics:
- Server should publish to: `dudkate@yandex.ru/123456/client/status`
- Client should subscribe to: `dudkate@yandex.ru/123456/client/status`

## Expected Flow
1. Server starts and subscribes to: `{prefix}/server/*`
2. Client connects and subscribes to: `{prefix}/client/*`  
3. Client publishes registration: `{prefix}/server/status` → `register|id|hostname`
4. Server receives and processes registration
5. Server calls `register_client()` method
6. Server publishes role assignment: `{prefix}/client/status` → `role|id|controller`
7. Client receives role and starts screen sharing

## Files with Enhanced Debugging
- `server.py` - Added extensive debugging to message handling
- `test_mqtt_flow.py` - New MQTT connectivity test
- Server status publishing reduced from every 150ms to every 4.5 seconds