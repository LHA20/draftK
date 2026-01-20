# Serial Port Integration Guide - Arduino/ESP32 RFID Card Scanner

## Overview

The Parking Management System now supports automatic license plate capture and check-in/out operations triggered by RFID card scans from Arduino or ESP32 microcontrollers. This eliminates the need for manual button clicks and enables fully automated parking operations.

## Hardware Requirements

- **Arduino/ESP32** microcontroller with RFID reader module
- **USB connection** to computer running the parking management system
- **Standard Serial Communication** (TTL/USB serial adapter if needed)

## Software Architecture

### New Components Added

1. **SerialSignals Class** - Qt signals for thread-safe communication
   - `data_received(dict)` - Emits parsed JSON card data
   - `connection_status(bool, str)` - Connection status changes
   - `error_signal(str)` - Error messages

2. **SerialWorker Thread** - Background thread listening for card scans
   - Auto-connects to specified port and baud rate
   - Parses incoming JSON data
   - Emits signals to main UI thread

3. **UI Controls** - Serial configuration panel
   - Serial port dropdown (auto-detects connected devices)
   - Baud rate selection (9600, 19200, 38400, 57600, 115200)
   - Connect/Disconnect button
   - Connection status indicator (🟢/🔴)

4. **Event Handler** - Automatic operations on card scan
   - Auto-captures license plate via YOLO detection
   - Performs check-in or check-out based on gate direction
   - Updates parking records automatically

## JSON Message Format

### Card Scan Event

When a card is scanned, send JSON data in this format:

```json
{
  "event": "CARD_SCAN",
  "uid": "A1B2C3D4",
  "gate": "ENTRY",
  "slot": 1
}
```

**Fields:**
- `event` (string): Always "CARD_SCAN" for card scan events
- `uid` (string): Unique card ID (RFID UID hex string)
- `gate` (string): Direction - "ENTRY" for check-in, "EXIT" for check-out
- `slot` (integer): Parking slot number (1-100)

### Example Scenarios

**Vehicle Entering Parking Lot:**
```json
{"event":"CARD_SCAN","uid":"A1B2C3D4","gate":"ENTRY","slot":5}
```
- System auto-captures license plate
- Saves as vehicle entry record
- Calculates parking start time

**Vehicle Exiting Parking Lot:**
```json
{"event":"CARD_SCAN","uid":"A1B2C3D4","gate":"EXIT","slot":5}
```
- System auto-captures license plate (for verification)
- Finds corresponding entry record
- Calculates parking duration and fee
- Marks as exit and saves record

## Arduino/ESP32 Example Code

### Arduino with RFID-RC522 Module

```cpp
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

// RFID module pins
#define SS_PIN 10
#define RST_PIN 9
MFRC522 rfid(SS_PIN, RST_PIN);

// Gate configuration (change as needed for each gate)
const char* GATE_NAME = "ENTRY";  // Change to "EXIT" for exit gate
const int SLOT_NUMBER = 1;

void setup() {
  Serial.begin(9600);  // Match baud rate in parking system
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("RFID Reader ready - waiting for cards...");
}

void loop() {
  // Check for RFID card
  if (rfid.PICC_IsNewCardPresent()) {
    if (rfid.PICC_ReadCardSerial()) {
      // Read card UID
      String uid = "";
      for (int i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) uid += "0";
        uid += String(rfid.uid.uidByte[i], HEX);
      }
      uid.toUpperCase();
      
      // Create JSON payload
      StaticJsonDocument<200> doc;
      doc["event"] = "CARD_SCAN";
      doc["uid"] = uid;
      doc["gate"] = GATE_NAME;
      doc["slot"] = SLOT_NUMBER;
      
      // Send to parking system
      serializeJson(doc, Serial);
      Serial.println();  // Add newline to complete message
      
      // Brief feedback (optional)
      delay(500);
      rfid.PICC_HaltA();
      rfid.PCD_StopCrypto1();
    }
  }
}
```

### ESP32 with RFID-RC522 Module

```cpp
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

// ESP32 pin assignments
#define SS_PIN 5
#define RST_PIN 4
MFRC522 rfid(SS_PIN, RST_PIN);

// Gate configuration
const char* GATE_NAME = "ENTRY";
const int SLOT_NUMBER = 1;

void setup() {
  Serial.begin(115200);  // ESP32 default baud rate
  delay(1000);
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("ESP32 RFID Reader ready");
}

void loop() {
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    // Convert UID to hex string
    String uid = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
      if (rfid.uid.uidByte[i] < 0x10) uid += "0";
      uid += String(rfid.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();
    
    // Build JSON
    StaticJsonDocument<200> doc;
    doc["event"] = "CARD_SCAN";
    doc["uid"] = uid;
    doc["gate"] = GATE_NAME;
    doc["slot"] = SLOT_NUMBER;
    
    // Send to parking system
    serializeJson(doc, Serial);
    Serial.println();
    
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    delay(500);
  }
}
```

## System Configuration

### Step 1: Physical Connection

1. Connect Arduino/ESP32 to USB port on computer
2. Verify device appears in system device manager
3. Note the COM port (e.g., COM3, /dev/ttyUSB0)

### Step 2: Parking System Setup

1. Launch parking management system
2. In **🔌 ARDUINO/ESP32 CONFIGURATION** panel:
   - Click 🔄 button to detect available serial ports
   - Select correct COM port from dropdown
   - Choose appropriate baud rate (usually 9600 for Arduino, 115200 for ESP32)
3. Click **🔗 CONNECT** button
4. Status indicator should turn green (🟢 Connected)

### Step 3: Testing

1. Keep parking system running
2. Scan a test RFID card at Arduino/ESP32
3. System should:
   - Log incoming card data in console
   - Auto-fill Card ID field
   - Capture license plate automatically
   - Perform check-in or check-out based on gate
   - Update parking records

## Auto-Capture Workflow

When card scan is detected:

```
1. Serial data received (JSON)
   ↓
2. Parse JSON and extract: uid, gate, slot
   ↓
3. Update UI fields:
   - Card ID ← uid
   - Parking Slot ← slot
   ↓
4. Trigger license plate capture (300ms delay)
   - YOLO detects license plate in current frame
   - OCR extracts text
   - Saves full frame + cropped image
   ↓
5. Auto check-in or check-out (1500ms delay)
   - If gate == "ENTRY": Check In
   - If gate == "EXIT": Check Out
   ↓
6. Update parking records
   - Save to CSV
   - Update UI table
   - Calculate and store fee
```

## Connection Status Indicators

### 🟢 Green (Connected)
- Serial port successfully opened
- Listening for incoming data
- System ready for card scans

### 🔴 Red (Disconnected)
- Port closed or unreachable
- No data being received
- Card scans will not be processed

## Troubleshooting

### Port Not Detected
**Problem:** Dropdown shows "No ports found"
- Solution: 
  - Check USB cable connection
  - Verify device drivers installed (CH340 for Arduino clones)
  - Try different USB port on computer
  - Click 🔄 Refresh button

### Connection Fails
**Problem:** Error "Serial connection error"
- Solution:
  - Verify baud rate matches Arduino code (usually 9600)
  - Check if port is used by another application
  - Try using Device Manager to verify port number
  - Restart Arduino/ESP32 device

### No Data Received
**Problem:** Card scans don't appear in system
- Solution:
  - Verify card is being detected by Arduino/ESP32
  - Check JSON message format in Arduino serial monitor
  - Confirm newline character is sent after JSON
  - Verify gate name is "ENTRY" or "EXIT" (case-sensitive)

### License Plate Not Captured
**Problem:** Card scanned but license plate not captured
- Solution:
  - Ensure camera is pointing at correct area
  - Check YOLO model is loaded (check console output)
  - Verify lighting is adequate for plate detection
  - Test manual capture button first to verify camera works

### Check-out Finds No Entry Record
**Problem:** Exit card scan but error "Not found in parking"
- Solution:
  - Verify card UID matches previous entry record
  - Check slot number is same for entry and exit
  - Verify time hasn't reset between entry and exit
  - Check CSV file for existing records

## Performance Notes

- **JSON Parsing:** Real-time, <50ms
- **License Plate Capture:** 200-500ms depending on YOLO inference
- **Check-in/out Processing:** <100ms for database operations
- **Auto-trigger Delays:**
  - License capture: 300ms after card scan
  - Check-in/out: 1500ms after card scan (allows capture to complete)

## Security Considerations

- RFID UIDs are transmitted in plain text via serial
- Consider adding encryption for production deployments
- Keep USB port physically secure
- Log all card scan events for audit trail

## Multi-Gate Setup

For multi-gate parking lots with separate entry and exit:

1. Deploy one Arduino/ESP32 at entry gate
   - Set `GATE_NAME = "ENTRY"`
   - Set `SLOT_NUMBER = 1-50` (entry side slots)

2. Deploy another Arduino/ESP32 at exit gate
   - Set `GATE_NAME = "EXIT"`
   - Set `SLOT_NUMBER = 1-50` (same slot numbering)

3. Run parking system on computer with two serial ports connected
4. Use port dropdown to switch between entry/exit gates

## Future Enhancements

- Support for multiple simultaneous serial connections (for multi-gate)
- Event logging and analytics dashboard
- Real-time capacity monitoring
- Mobile app integration
- Cloud database synchronization

## Version History

- **v3.3** (2026-01-15): Initial serial port integration
  - Auto-detect serial ports
  - JSON card scan parsing
  - Automatic license plate capture
  - Smart check-in/out based on gate direction
