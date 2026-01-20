# Quick Start Guide - v3.3

## 30-Second Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Connect Hardware
- Plug Arduino/ESP32 RFID reader into USB port

### 3. Run Application
```bash
python main_parking.py
```

### 4. Connect to Serial Port
- Select port from dropdown
- Click "🔗 CONNECT"
- Wait for "🟢 Connected"

### 5. Start Scanning Cards
- Scan RFID card at entrance
- System automatically captures license plate
- Vehicle checked in (green row in table)
- Scan same card at exit
- Fee calculated automatically
- Vehicle checked out (red row in table)

## Key Features at a Glance

| Feature | Manual | Auto | Time |
|---------|--------|------|------|
| Check-in | Button | Card Scan | 1-2s |
| Check-out | Button | Card Scan | 1-2s |
| License Plate | Manual Entry | Auto-detect | N/A |
| Fee Calculation | Manual | Automatic | N/A |
| CSV Save | Auto | Auto | Auto |

## System Flow Diagram

```
┌─────────────────────────────────────────────────┐
│           Parking Management System             │
│                   v3.3                          │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
    ┌───▼────┐         ┌──────▼─────┐
    │ Arduino/│         │  USB       │
    │ ESP32   │◄────────┤  Webcam    │
    │ RFID    │         └────────────┘
    └───┬────┘
        │
        │ JSON: {"event":"CARD_SCAN",
        │        "uid":"A1B2C3D4",
        │        "gate":"ENTRY",
        │        "slot":1}
        │
    ┌───▼──────────────────────────┐
    │  PyQt5 Application Main UI   │
    │  • Live Video Feed           │
    │  • License Plate Snapshot    │
    │  • Parking Records Table     │
    │  • Fee Display               │
    └───┬───────────────────┬──────┘
        │                   │
   ┌────▼────┐       ┌──────▼─────┐
   │ YOLO    │       │  EasyOCR   │
   │ License │       │  Text      │
   │ Plate   │       │ Extraction │
   │Detection│       └────────────┘
   └────┬────┘
        │
   ┌────▼──────────────────────┐
   │  Automatic Processing:    │
   │  • Check-in (ENTRY gate)  │
   │  • Check-out (EXIT gate)  │
   │  • Fee Calculation        │
   │  • CSV Save               │
   └────┬──────────────────────┘
        │
   ┌────▼──────────────────────┐
   │  Data Storage:            │
   │  • CSV: parking_records   │
   │  • JPG: captured_images   │
   │  • XLS: Excel Export      │
   └───────────────────────────┘
```

## Console Output Reference

### Startup Messages
```
✓ License plate detector model loaded
✓ Camera initialized
✓ System ready
```

### When Card is Scanned
```
📱 Card event received: ID=A1B2C3D4, Gate=ENTRY, Slot=1
Card scanned: A1B2C3D4 - Gate: ENTRY
✓ Captured images saved: 20260120_103045_123
✅ License plate extracted: ABC123XYZ (Confidence: 0.95)
✅ AUTO CHECK-IN: A1B2C3D4 | Plate: ABC123XYZ | Slot: 1
```

### When Exit Happens
```
📱 Card event received: ID=A1B2C3D4, Gate=EXIT, Slot=1
Card scanned: A1B2C3D4 - Gate: EXIT
✅ License plate extracted: ABC123XYZ (Confidence: 0.95)
✅ AUTO CHECK-OUT: ABC123XYZ | Card: A1B2C3D4 | Fee: 25,000 VND
```

## UI Elements Explained

### Left Panel
```
┌─────────────────────────┐
│  LIVE CAMERA FEED       │ ◄─── Real-time video (30 FPS)
│  [Live Video Display]   │
├─────────────────────────┤
│ CAPTURED LICENSE PLATE  │ ◄─── Screenshot of detected plate
│  [Snapshot Image]       │
├─────────────────────────┤
│ EXTRACTED TEXT          │ ◄─── OCR result (purple box)
│    ABC123XYZ            │     Large, bold text
└─────────────────────────┘
```

### Right Panel
```
┌──────────────────────────────────────┐
│  ARDUINO/ESP32 CONFIGURATION         │ ◄─── New in v3.3
│  Port: /dev/ttyUSB0     [Refresh]    │
│  Baud Rate: 9600                     │
│  Status: 🟢 Connected   [DISCONNECT] │
├──────────────────────────────────────┤
│  CHECK IN - VEHICLE ENTRY            │
│  Card ID: [_________________]         │
│  Parking Slot: [_________________]   │
│  [CAPTURE LICENSE PLATE] [CHECK IN]  │
├──────────────────────────────────────┤
│  CHECK OUT - VEHICLE EXIT            │
│  License Plate: [_________________]  │
│  [CHECK OUT]                         │
├──────────────────────────────────────┤
│  TRANSACTION INFORMATION             │
│  Status: ✓ System Ready              │
│  💰 PARKING FEE: 0 VND               │
├──────────────────────────────────────┤
│  PARKING RECORDS & HISTORY           │
│  [Table with 7 columns]              │
│  • Card ID | Plate | In | Out | Slot│
│  • Status | Fee                      │
├──────────────────────────────────────┤
│  DATA MANAGEMENT                     │
│  [DOWNLOAD EXCEL REPORT]             │
└──────────────────────────────────────┘
```

## Common Tasks

### Task 1: Connect to Arduino
1. Plug Arduino into USB
2. Open application
3. Port should auto-populate
4. Click "🔗 CONNECT"
5. Wait for "🟢 Connected"

### Task 2: Scan Cards
1. Position RFID reader near antenna
2. Scan card at entrance
3. Watch for auto check-in
4. Scan same card at exit
5. Fee automatically calculated

### Task 3: Manual Entry (if Scanner Down)
1. Click "🔌 DISCONNECT" (if connected)
2. Point camera at license plate
3. Click "📸 CAPTURE LICENSE PLATE"
4. Enter Card ID manually
5. Enter Slot Number manually
6. Click "✅ CHECK IN"

### Task 4: Manual Exit
1. Enter License Plate manually
2. Click "🏁 CHECK OUT"
3. Fee displays automatically

### Task 5: Download Report
1. Click "💾 DOWNLOAD EXCEL REPORT"
2. Choose save location
3. Excel file opens with:
   - All records from today
   - Colored status (green IN, red OUT)
   - Calculated fees
   - Professional formatting

## Troubleshooting

### Problem: Serial Port Not Found
**Solution:**
1. Plug Arduino into different USB port
2. Click "🔄" refresh button
3. Check Device Manager (Windows) or `lsusb` (Linux)

### Problem: "No license plate detected"
**Solution:**
1. Improve lighting
2. Position camera higher
3. Angle camera 30-45 degrees down
4. Clean camera lens

### Problem: OCR Extraction Fails
**Solution:**
1. Move camera closer to plate
2. Ensure plate is clean
3. Check text is in English
4. Try manual capture first

### Problem: Connection Drops
**Solution:**
1. Check USB cable
2. Try different USB port
3. Restart application
4. Replace USB cable if faulty

### Problem: Fee Calculation Wrong
**Solution:**
1. Check Time In and Time Out are correct
2. Verify fee formula: < 2h = 20k, +10k per hour
3. Check if checkout was successful
4. Review console for errors

## File Locations

| File | Purpose | Location |
|------|---------|----------|
| Application | Main program | `main_parking.py` |
| Config | Dependencies | `requirements.txt` |
| Records | CSV database | `parking_records.csv` |
| Images | Captured frames | `captured_images/` |
| YOLO Model | Plate detection | `Automatic-License-.../license_plate_detector.pt` |

## Default Settings

| Setting | Value | Range |
|---------|-------|-------|
| Baud Rate | 9600 | 9600, 19200, 38400, 57600, 115200 |
| Camera FPS | 30 | N/A |
| Minimum Plate Text Length | 4 characters | N/A |
| Fee < 2h | 20,000 VND | N/A |
| Fee per hour (>2h) | +10,000 VND | N/A |
| Serial Timeout | 1 second | N/A |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Tab | Focus next field |
| Enter | Confirm/Submit |
| Esc | Cancel (in some dialogs) |

## Performance Tips

1. **Faster Detection:**
   - Use USB 3.0 port for camera
   - Use baud rate 115200 for serial
   - Ensure good lighting

2. **Better Accuracy:**
   - Clean camera lens regularly
   - Position camera consistently
   - Ensure license plates are clear

3. **Reliable Operation:**
   - Keep USB cables secure
   - Use quality Arduino boards
   - Regular backups of CSV

## Getting Help

### Check These Files First
1. **Technical Details:** `SERIAL_INTEGRATION_COMPLETE_v3.3.md`
2. **Test Scenarios:** `TESTING_GUIDE_v3.3.md`
3. **What's New:** `v3.3_RELEASE_COMPLETE.md`

### Debug Information
1. Check console output for error messages
2. Review `/captured_images/` folder for captures
3. Open `parking_records.csv` to verify data
4. Check system time/date settings

### Common Messages Explained

| Message | Meaning | Action |
|---------|---------|--------|
| "🟢 Connected" | Serial port ready | System is operational |
| "Card scanned:" | RFID detected | Watch for auto check-in |
| "No license plate detected" | YOLO found nothing | Reposition camera |
| "OCR failed" | Text not extracted | Verify plate clarity |
| "🔴 Disconnected" | Serial connection lost | Click CONNECT button |

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Connect hardware (Arduino + Camera)
3. ✅ Run: `python main_parking.py`
4. ✅ Connect serial port
5. ✅ Scan first test card
6. ✅ Download Excel report
7. 📖 Read detailed guides if needed

## Support

For detailed information:
- **Installation Issues:** See `INSTALLATION_GUIDE.md`
- **Serial Integration:** See `SERIAL_INTEGRATION_COMPLETE_v3.3.md`
- **Testing:** See `TESTING_GUIDE_v3.3.md`
- **Troubleshooting:** See `TROUBLESHOOTING.md`

---

**Ready to Go!** 🚀

Your parking management system is configured and ready to handle card scans automatically. Start scanning RFID cards and watch the system work!

**Version 3.3** | **January 20, 2026** | ✅ Production Ready
