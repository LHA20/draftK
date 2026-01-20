# Serial Communication Quick Reference

## JSON Message Format

### Card Scan Event

```
{
  "event": "CARD_SCAN",
  "uid": "A1B2C3D4",
  "gate": "ENTRY",
  "slot": 1
}
```

**Transmission format:** JSON string followed by newline character (\\n)

Example in Arduino:
```cpp
serializeJson(doc, Serial);
Serial.println();  // Adds newline
```

## Field Definitions

| Field | Type | Values | Example |
|-------|------|--------|---------|
| event | string | "CARD_SCAN" | "CARD_SCAN" |
| uid | string | Card ID (4-32 chars) | "5F2C1A9E" |
| gate | string | "ENTRY" or "EXIT" | "ENTRY" |
| slot | integer | 1-100 | 5 |

## System Behavior

### On ENTRY Gate (gate: "ENTRY")

1. ✓ License plate auto-captured
2. ✓ Card ID auto-filled
3. ✓ Check-in recorded automatically
4. ✓ Parking start time recorded
5. ✓ Record saved to CSV and database

### On EXIT Gate (gate: "EXIT")

1. ✓ License plate auto-captured
2. ✓ Looks up entry record by UID
3. ✓ Check-out recorded automatically
4. ✓ Parking duration calculated
5. ✓ Fee calculated (< 2h: 20k VND, +10k per hour)
6. ✓ Record updated with exit time and fee

## Serial Port Configuration

| Parameter | Values | Default |
|-----------|--------|---------|
| Baud Rate | 9600, 19200, 38400, 57600, 115200 | 9600 |
| Data Bits | 8 | 8 |
| Stop Bits | 1 | 1 |
| Parity | None | None |
| Flow Control | None | None |

## Status Indicators

| Indicator | Meaning | Action |
|-----------|---------|--------|
| 🟢 Connected | Serial port active | System ready for cards |
| 🔴 Disconnected | No connection | Click CONNECT to activate |

## UI Controls

### Serial Configuration Panel

| Control | Function |
|---------|----------|
| Port Dropdown | Select USB serial device |
| 🔄 Refresh | Rescan for new USB devices |
| Baud Rate Dropdown | Select communication speed |
| Status Indicator | Shows connection status |
| 🔗 CONNECT / 🔌 DISCONNECT | Toggle connection |

## Common JSON Examples

### Vehicle Entry
```json
{"event":"CARD_SCAN","uid":"5F2C1A9E","gate":"ENTRY","slot":5}
```
- Slot 5, vehicle entering parking
- License plate auto-captured
- Entry recorded with current timestamp

### Vehicle Exit
```json
{"event":"CARD_SCAN","uid":"5F2C1A9E","gate":"EXIT","slot":5}
```
- Slot 5, same vehicle leaving
- License plate auto-captured for verification
- Exit recorded, fee calculated (based on duration)

### Multiple Gates Entry
```json
{"event":"CARD_SCAN","uid":"1A2B3C4D","gate":"ENTRY","slot":12}
```
- Different card, different slot
- Independent entry record created

### Batch Processing
```
{"event":"CARD_SCAN","uid":"AAAA","gate":"ENTRY","slot":1}
{"event":"CARD_SCAN","uid":"BBBB","gate":"ENTRY","slot":2}
{"event":"CARD_SCAN","uid":"AAAA","gate":"EXIT","slot":1}
```
- Multiple cards processed sequentially
- System handles each event independently

## Error Messages

### Port Detection Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "No ports found" | No USB devices | Connect Arduino/ESP32 |
| "Device busy" | Port in use elsewhere | Close other serial apps |
| "Access denied" | Permission issue | Run as administrator |

### Connection Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid baud rate" | Mismatch | Check Arduino code |
| "Connection timeout" | No data | Check USB cable |
| "Port disconnected" | Device removed | Reconnect device |

### JSON Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid JSON" | Malformed message | Check Arduino JSON format |
| "Missing field" | Missing required key | Check all 4 fields present |
| "Invalid gate value" | Not ENTRY/EXIT | Use exact spelling |

## Python API (For Custom Integration)

### Get Available Ports
```python
from parking import get_available_ports

ports = get_available_ports()
for port_name, description in ports:
    print(f"{port_name}: {description}")
```

### Start Serial Connection
```python
from parking import SerialWorker, SerialSignals

signals = SerialSignals()
worker = SerialWorker(signals)
worker.set_connection('/dev/ttyUSB0', 9600)
worker.start()
```

### Handle Card Scans
```python
def on_card_scanned(data):
    card_id = data['uid']
    gate = data['gate']
    slot = data['slot']
    print(f"Card {card_id} {gate} at slot {slot}")

signals.data_received.connect(on_card_scanned)
```

## Arduino Code Snippets

### RFID UID to String (Arduino)
```cpp
String uid = "";
for (int i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
}
uid.toUpperCase();
```

### Send JSON (Arduino)
```cpp
#include <ArduinoJson.h>

StaticJsonDocument<200> doc;
doc["event"] = "CARD_SCAN";
doc["uid"] = uid;
doc["gate"] = "ENTRY";
doc["slot"] = 5;

serializeJson(doc, Serial);
Serial.println();  // Important: newline terminates message
```

### Send JSON (ESP32)
```cpp
StaticJsonDocument<200> doc;
doc["event"] = "CARD_SCAN";
doc["uid"] = uid;
doc["gate"] = GATE_NAME;
doc["slot"] = SLOT_NUMBER;

serializeJson(doc, Serial);
Serial.println();
```

## Performance Targets

| Operation | Target | Typical |
|-----------|--------|---------|
| JSON parse | <50ms | 20ms |
| License capture | <500ms | 300ms |
| Check-in/out | <100ms | 50ms |
| Record save | <100ms | 30ms |
| **Total** | **<1500ms** | **~1000ms** |

## Troubleshooting Commands

### Linux/Mac - List Serial Ports
```bash
ls -la /dev/tty* | grep -E "USB|ACM"
```

### Windows - List Serial Ports (PowerShell)
```powershell
Get-WmiObject Win32_SerialPort | Select Name, Description
```

### Monitor Serial Data (Linux)
```bash
stty -F /dev/ttyUSB0 9600 raw
cat /dev/ttyUSB0
```

### Test Serial Connection (Python)
```bash
python3 test_serial_port.py
```

## License Plate Capture Details

When a card is scanned:

1. **Timing:** Triggered 300ms after card detection
2. **Source:** Current video frame from camera
3. **Detection:** YOLO license plate detector
4. **Recognition:** EasyOCR text extraction
5. **Output:**
   - Full frame → `captured_images/full_frame_TIMESTAMP.jpg`
   - Plate crop → `captured_images/license_plate_TIMESTAMP.jpg`
6. **Fallback:** Manual entry if auto-capture fails

## Data Recording

Automatically saved fields:
- **Card ID** - From JSON uid field
- **License Plate** - From YOLO + OCR
- **Time In** - Current timestamp
- **Slot** - From JSON slot field
- **Gate** - From JSON gate field (ENTRY/EXIT)
- **Time Out** - On exit, current timestamp
- **Fee** - On exit, calculated amount

Saved to:
- CSV: `parking_records.csv`
- Excel: Auto-generated on export

## Version Support

- **Parking System:** v3.3+
- **Python:** 3.8+
- **PySerial:** 3.5+
- **Arduino IDE:** 1.8+
- **ESP32 Arduino Core:** 2.0+

---

**Last Updated:** 2026-01-15
**Maintained By:** Parking System Development Team
