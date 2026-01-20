# Testing Guide - Serial Port Integration v3.3

## Quick Test Setup

### Minimum Requirements
- Python 3.7+
- Arduino/ESP32 with RFID reader and USB serial connection
- Webcam for license plate detection
- All dependencies from `requirements.txt`

### Dependencies Installation
```bash
pip install -r requirements.txt
```

## Test Scenarios

### Scenario 1: Manual Testing (Without Arduino)

**Simulate card scan via Python script:**

```python
import serial
import json
import time

# Connect to the same port application is using
ser = serial.Serial('/dev/ttyUSB0', 9600)  # Adjust port as needed
time.sleep(1)

# Send ENTRY event
card_data = {
    "event": "CARD_SCAN",
    "uid": "CARD001",
    "gate": "ENTRY",
    "slot": 1
}
ser.write((json.dumps(card_data) + '\n').encode())
print("Sent ENTRY event for CARD001")

# Wait 10 seconds
time.sleep(10)

# Send EXIT event (same card)
card_data = {
    "event": "CARD_SCAN",
    "uid": "CARD001",
    "gate": "EXIT",
    "slot": 1
}
ser.write((json.dumps(card_data) + '\n').encode())
print("Sent EXIT event for CARD001")

ser.close()
```

**Save as `test_serial_send.py` and run:**
```bash
python test_serial_send.py
```

### Scenario 2: Full Workflow Test

**Expected behavior:**

1. **Startup**
   - Application starts
   - Serial ports detected and listed
   - Default port selected (if available)
   - Baud rate set to 9600

2. **Connect to Arduino**
   - Select correct port from dropdown
   - Click "🔗 CONNECT" button
   - Status changes to "🟢 Connected"
   - Button changes to "🔌 DISCONNECT"

3. **Send ENTRY Card**
   - Arduino sends: `{"event":"CARD_SCAN","uid":"CARD001","gate":"ENTRY","slot":1}`
   - UI shows: "Card scanned (CARD001) - ENTRY | Capturing license plate..."
   - Camera captures frame
   - YOLO detects license plate
   - OCR extracts text (e.g., "ABC123XYZ")
   - Record created in table (green row)
   - Status shows: "✓ CARD001 checked in successfully"
   - CSV updated with entry

4. **Send EXIT Card**
   - Arduino sends: `{"event":"CARD_SCAN","uid":"CARD001","gate":"EXIT","slot":1}`
   - UI shows: "Card scanned (CARD001) - EXIT | Capturing license plate..."
   - Same license plate captured
   - System finds existing entry in table
   - Calculates fee based on duration
   - Updates record (red row, adds fee)
   - Status shows: "✓ ABC123XYZ checked out | Fee: 25,000 VND"
   - CSV updated with exit and fee

5. **Download Excel**
   - Click "💾 DOWNLOAD EXCEL REPORT"
   - Select save location
   - File opens with:
     - Header with generation timestamp
     - Colored status columns (green IN, red OUT)
     - Formatted fee column (right-aligned)
     - Frozen header row

### Scenario 3: Edge Cases

#### Test 3.1: No License Plate Detected
1. Position camera where no plate is visible
2. Send card event
3. **Expected:** Status shows "No license plate detected"
4. **Record:** NOT saved to table
5. **Next:** System ready for next card

#### Test 3.2: OCR Extraction Fails
1. Send card with very blurry license plate image
2. **Expected:** Status shows "OCR failed - no text extracted"
3. **Record:** NOT saved to table
4. **Next:** System ready for next card

#### Test 3.3: Check-out of Never-Checked-In Vehicle
1. Send EXIT event for new card
2. **Expected:** Status shows "No vehicle with plate found"
3. **Record:** NOT saved
4. **Next:** System ready for next card

#### Test 3.4: Duplicate Entry Prevention
1. Send ENTRY for card CARD001
2. Immediately send another ENTRY for CARD001
3. **Expected:** Second entry rejected with message "already checked in"
4. **Result:** Only first entry in table

#### Test 3.5: Serial Disconnect
1. Connect to serial port
2. Physically unplug Arduino/USB cable
3. **Expected:** 
   - Status changes to "🔴 Disconnected"
   - Error message appears
   - Button becomes "🔗 CONNECT" again
4. **Recovery:** Plug back in, click CONNECT

#### Test 3.6: Invalid JSON Format
1. Send malformed JSON: `{"event":"CARD_SCAN","uid":NOTASTRING}`
2. **Expected:** Error logged, system continues listening
3. **Result:** No error message shown to user (robust)

#### Test 3.7: Missing Fields in JSON
1. Send: `{"event":"CARD_SCAN","uid":"CARD001"}` (missing gate and slot)
2. **Expected:** Card data still received but processed with defaults
3. **Gate:** Defaults to "ENTRY"
4. **Slot:** Empty string (for now)

### Scenario 4: Performance Test

**Send rapid card events:**

```python
import serial
import json
import time

ser = serial.Serial('/dev/ttyUSB0', 9600)
time.sleep(1)

for i in range(10):
    card_id = f"CARD{i:03d}"
    
    # Entry
    entry = {"event": "CARD_SCAN", "uid": card_id, "gate": "ENTRY", "slot": i+1}
    ser.write((json.dumps(entry) + '\n').encode())
    time.sleep(2)  # Wait for processing
    
    # Exit
    exit_event = {"event": "CARD_SCAN", "uid": card_id, "gate": "EXIT", "slot": i+1}
    ser.write((json.dumps(exit_event) + '\n').encode())
    time.sleep(2)  # Wait for processing
    
    print(f"Processed card {i+1}/10")

ser.close()
print("✅ All 10 vehicles processed successfully")
```

**Expected results:**
- All 10 entries and exits recorded
- No dropped events
- Parking fees calculated correctly
- All records in CSV and table

### Scenario 5: Manual Fallback

When serial port disconnected, verify manual workflow:

1. **Capture plate manually**
   - Click "📸 CAPTURE LICENSE PLATE"
   - License plate appears in snapshot
   - Text extracted and displayed

2. **Manual check-in**
   - Enter Card ID manually
   - Enter Slot manually
   - Click "✅ CHECK IN"
   - Record saved to table

3. **Manual check-out**
   - Enter License Plate manually
   - Click "🏁 CHECK OUT"
   - Fee calculated and displayed
   - Record updated in table

## Verification Checklist

### Files Generated
- [ ] `/captured_images/full_frame_*.jpg` exists
- [ ] `/captured_images/license_plate_*.jpg` exists
- [ ] `/parking_records.csv` updated with new records
- [ ] Excel export file created with correct data

### Database Records
- [ ] Each card scan creates one table entry
- [ ] Entry records show green "IN" status
- [ ] Exit records show red "OUT" status
- [ ] Fee calculated correctly (20k base + 10k/hour over 2h)
- [ ] Timestamps correct (HH:MM:SS format)

### UI Updates
- [ ] Port dropdown populated on startup
- [ ] Connection status indicator changes color
- [ ] Card data auto-filled from JSON
- [ ] License plate displayed in snapshot area
- [ ] Extracted text shown in purple box
- [ ] Status messages update in real-time
- [ ] Table refreshes after each transaction

### Console Output
- [ ] "✓ Camera initialized" on startup
- [ ] "✓ Serial port connected: /dev/ttyUSB0 @ 9600 baud" when connected
- [ ] "Card scanned: CARD001 - Gate: ENTRY" when card received
- [ ] "✅ License plate extracted: ABC123XYZ (Confidence: 0.95)" when success
- [ ] "✅ AUTO CHECK-IN: ..." when entry processed
- [ ] "✅ AUTO CHECK-OUT: ..." with fee when exit processed

## Debugging Tips

### Enable Verbose Logging
Add to console to see detailed messages:
```python
# Print before important operations
print(f"DEBUG: Card data = {self.pending_card_data}")
print(f"DEBUG: Current frame shape = {self.current_frame.shape}")
print(f"DEBUG: YOLO detections = {len(detections.boxes)}")
```

### Serial Port Debugging
Check available ports:
```bash
# Linux/Mac
ls /dev/tty*

# Windows
python -m serial.tools.list_ports
```

Test serial communication directly:
```bash
# Linux/Mac - use screen
screen /dev/ttyUSB0 9600

# Windows - use PuTTY or similar
```

### Capture Debugging
Verify images saved:
```bash
ls -lh captured_images/
file captured_images/*.jpg
```

### CSV Verification
Check parking records:
```bash
cat parking_records.csv
```

## Troubleshooting

### Serial Port Not Detected
1. Check USB cable connection
2. Verify Arduino/ESP32 drivers installed
3. Try different USB port
4. Restart application
5. Click "🔄" refresh button

### Connection Fails Immediately
1. Check baud rate matches device
2. Verify port not in use by other program
3. Check for permission issues: `sudo chmod 666 /dev/ttyUSB0`
4. Try different baud rate

### No License Plate Detected
1. Ensure lighting is adequate
2. Check camera positioning (plate should be front-center)
3. Verify YOLO model loaded: Check startup logs for "✓ License plate detector model loaded"
4. Try manual capture with button to test YOLO

### OCR Extraction Fails
1. Check image quality in `captured_images/` folder
2. Verify plate is clean and readable
3. Check OCR model loaded: Startup message "✓ Loading OCR reader"
4. Ensure text is English/Latin characters

### Records Not Saved
1. Check `/parking_records.csv` file permissions
2. Verify `captured_images/` directory writable
3. Check console for error messages
4. Ensure sufficient disk space

## Performance Optimization

### For Faster Processing
1. Use baud rate 115200 (faster serial communication)
2. Optimize camera resolution (currently 1280x720)
3. Use GPU for YOLO if available

### For More Accuracy
1. Improve lighting around parking area
2. Ensure license plates face camera directly
3. Clean camera lens regularly
4. Position camera at 30-45 degree angle

## Conclusion

This testing guide covers all major workflows and edge cases. Successful completion of all scenarios ensures the system is working correctly and ready for production use.

---

**Version:** 3.3  
**Last Updated:** January 20, 2026  
**Test Status:** Ready for QA ✅
