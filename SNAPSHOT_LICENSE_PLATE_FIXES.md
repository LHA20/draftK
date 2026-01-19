# 🔧 Snapshot & License Plate Extraction Fixes - v3.2

**Date:** January 12, 2026  
**Status:** ✅ Complete & Tested

---

## 📋 Changes Made

### 1. Snapshot Display (Now Works!)

**Before:**
```python
self.snapshot_label.setText("No snapshot yet")  # Just text, no image
```

**After:**
```python
# Actually display the captured image
rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
h, w, ch = rgb_crop.shape
bytes_per_line = 3 * w
qt_image = QImage(rgb_crop.data, w, h, bytes_per_line, QImage.Format_RGB888)
pixmap = QPixmap.fromImage(qt_image)
scaled_pixmap = pixmap.scaledToWidth(380, Qt.SmoothTransformation)
self.snapshot_label.setPixmap(scaled_pixmap)  # Display image
```

**Result:**
- ✅ When user clicks "CAPTURE LICENSE PLATE", the cropped license plate image displays
- ✅ Image is properly scaled to 380px width
- ✅ Shows only the detected license plate area (YOLO crop)

---

### 2. License Plate Auto-Extraction

**Before:**
```python
self.card_id_input.setText(plate_text)  # Wrong! Auto-filled Card ID with license plate
```

**After:**
```python
self.captured_license_plate = plate_text  # Store in variable
self.extracted_plate_label.setText(plate_text)  # Display in purple box
# Card ID input left empty for operator to manually enter
```

**Result:**
- ✅ License plate extracted via OCR is stored
- ✅ Displayed prominently in purple box
- ✅ Card ID field remains empty for operator input

---

### 3. Business Logic Fix

**Before:**
```python
record = {
    'card_id': card_id,
    'license_plate': card_id,  # Wrong! Using card_id as license_plate
    'time_in': now,
    ...
}
```

**After:**
```python
record = {
    'card_id': card_id,                              # Operator enters
    'license_plate': self.captured_license_plate,    # From OCR extraction
    'time_in': now,
    ...
}
```

**Result:**
- ✅ CSV records now have separate Card ID and License Plate
- ✅ License plate correctly captured from vehicle image
- ✅ Card ID correctly entered by operator

---

## 🔄 Updated Workflow

### VEHICLE ARRIVAL & CHECK-IN

```
1. 📹 VEHICLE ARRIVES
   ├─ Operator watches LIVE CAMERA FEED (top-left)
   └─ Vehicle's license plate visible on screen

2. 📸 OPERATOR CLICKS "CAPTURE LICENSE PLATE"
   ├─ System captures current video frame
   ├─ YOLO model detects license plate region
   ├─ Crops the detected plate area
   ├─ Displays SNAPSHOT (actual license plate image) below video
   └─ Status: "Processing..."

3. 🔤 OCR EXTRACTION COMPLETES
   ├─ EasyOCR reads the cropped image
   ├─ Extracts license plate text (e.g., "ABC123XYZ")
   ├─ Displays in EXTRACTED TEXT box (large, purple, bold)
   ├─ Status: "✓ License plate captured - ABC123XYZ"
   └─ Stored in memory: self.captured_license_plate

4. 🎫 OPERATOR ENTERS CARD ID
   ├─ Card ID input field is EMPTY (not auto-filled)
   ├─ Operator manually enters card number from parking ticket
   └─ Example: "CARD-2024-001234"

5. 🅿️ OPERATOR ENTERS SLOT NUMBER
   ├─ Slot input field
   ├─ Operator enters parking slot assigned
   └─ Example: "A1", "B5", "C12"

6. ✅ OPERATOR CLICKS "CHECK IN (IN)"
   ├─ System validates Card ID and Slot are entered
   ├─ System validates License Plate was captured
   ├─ Creates record with:
   │  ├─ card_id: operator-entered value (e.g., "CARD-2024-001234")
   │  ├─ license_plate: extracted from OCR (e.g., "ABC123XYZ")
   │  ├─ slot: operator-entered value (e.g., "A1")
   │  ├─ time_in: current timestamp
   │  ├─ status: "IN"
   │  └─ fee: 0
   ├─ Saves to CSV
   ├─ Updates table
   └─ Shows confirmation with all details

7. 📊 RECORD SAVED
   CSV now contains:
   ┌───────────────┬──────────────┬────────────┬─────┐
   │ Card ID       │ License Plate│ Time In    │ ... │
   ├───────────────┼──────────────┼────────────┼─────┤
   │CARD-2024-001 │ABC123XYZ     │10:30:45    │ ... │
   │CARD-2024-002 │XYZ789PQR     │10:45:20    │ ... │
   └───────────────┴──────────────┴────────────┴─────┘
```

---

## 🔍 Data Flow Explanation

### What Each Input Represents

| Field | Source | Example | Purpose |
|-------|--------|---------|---------|
| **Card ID** | Operator manually enters | CARD-2024-001234 | Identifies parking ticket/reservation |
| **License Plate** | Extracted via OCR from image | ABC-123-XYZ | Identifies the vehicle |
| **Slot Number** | Operator manually enters | A1, B5, C12 | Where vehicle is parked |
| **Time In** | System auto-set | 2026-01-12 10:30:45 | When vehicle entered |

### Why They're Separate

- **Card ID** = Parking ticket number (administrative)
- **License Plate** = Vehicle identifier (automatic extraction)
- **Slot** = Physical parking location (manual assignment)

This allows:
✅ Multiple vehicles can share same license plate (different times)
✅ Track which operator processed which vehicle (via card/ticket)
✅ Know exactly which spot each vehicle occupies
✅ Accurate fee calculation based on actual parking duration

---

## 💾 CSV Record Example

```
Card ID,License Plate,Time In,Time Out,Slot Number,Status,Fee (VND)
CARD-2024-001,ABC123XYZ,2026-01-12 10:30:45,,A1,IN,0
CARD-2024-002,XYZ789PQR,2026-01-12 11:15:20,,B5,IN,0
CARD-2024-001,ABC123XYZ,2026-01-12 10:30:45,2026-01-12 12:45:30,A1,OUT,30000
```

---

## 🧪 Testing the New Features

### Test Case 1: Snapshot Display

```
1. Run application
2. Observe live video feed (top-left)
3. Click "📸 CAPTURE LICENSE PLATE" button
4. ✓ Snapshot area below video shows cropped license plate image
5. ✓ Extracted text shows in purple box
6. ✓ Status updates with "License plate captured - [TEXT]"
```

### Test Case 2: Card ID vs License Plate

```
1. Capture license plate (extract "ABC123XYZ")
2. Observe:
   - License plate field is EMPTY (not auto-filled) ✓
   - Extracted text shows "ABC123XYZ" in purple ✓
3. Operator enters "CARD-2024-001" in Card ID
4. Operator enters "A1" in Slot
5. Click "CHECK IN (IN)"
6. ✓ Confirmation shows both values:
   - Card ID: CARD-2024-001
   - License Plate: ABC123XYZ
   - Slot: A1
```

### Test Case 3: CSV Record

```
1. Complete check-in with:
   - Card ID: "CARD-2024-001"
   - License Plate: "ABC123XYZ" (captured)
   - Slot: "A1"

2. Open parking_records.csv
   - Card ID column: CARD-2024-001 ✓
   - License Plate column: ABC123XYZ ✓
   - Slot column: A1 ✓
   - Status: IN ✓
```

---

## 🚀 Key Improvements Summary

| Aspect | Issue | Fix | Result |
|--------|-------|-----|--------|
| **Snapshot** | Not displaying | Convert crop to QPixmap & display | Shows actual captured image |
| **License Plate** | Auto-filled Card ID | Store separately, display in box | Operator sees extracted text, enters card ID manually |
| **Card ID** | Was set to license plate | Operator enters manually | Correct parking ticket tracking |
| **Business Logic** | Wrong data in CSV | Use captured_license_plate variable | Accurate vehicle identification |
| **User Experience** | Confusing workflow | Clear separation of inputs | Intuitive check-in process |

---

## 📋 Implementation Details

### New Variable Added

```python
self.captured_license_plate = None  # Store extracted license plate
```

### Snapshot Display Code

```python
# Convert OpenCV image to QPixmap
rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
h, w, ch = rgb_crop.shape
bytes_per_line = 3 * w
qt_image = QImage(rgb_crop.data, w, h, bytes_per_line, QImage.Format_RGB888)
pixmap = QPixmap.fromImage(qt_image)
scaled_pixmap = pixmap.scaledToWidth(380, Qt.SmoothTransformation)
self.snapshot_label.setPixmap(scaled_pixmap)
```

### Check-in Validation

```python
if not self.captured_license_plate:
    QMessageBox.warning(self, "Error", "Please capture license plate first")
    return
```

### Record Creation

```python
record = {
    'card_id': card_id,                         # Manual entry
    'license_plate': self.captured_license_plate,  # Auto-captured
    'time_in': now,
    'time_out': None,
    'slot': slot,
    'status': 'IN',
    'fee': 0
}
```

---

## 🔒 Data Integrity

### Check-in Validation
✅ Card ID required
✅ Slot Number required
✅ License Plate must be captured first
✅ Duplicate check-in prevention

### Check-out Validation
✅ License Plate lookup in CSV
✅ Status verification (must be "IN")
✅ Fee calculation accuracy
✅ Proper datetime handling

---

## 📖 UI Updates

### License Plate Display

**Location:** Bottom of left panel, below snapshot
**Size:** 380px wide
**Font:** Courier New, 16pt, Bold
**Colors:** Purple text (#6d28d9) on light purple background (#f3e8ff)
**Border:** 2px solid purple (#7c3aed)
**Update:** After OCR extraction completes

**States:**
- Initial: "Awaiting capture..."
- After capture: Extracted text (e.g., "ABC123XYZ")
- After failed capture: "OCR Failed"

---

## ✅ Verification Checklist

- [x] Snapshot displays captured image
- [x] License plate text extracted and displayed
- [x] Card ID field NOT auto-filled
- [x] Operator can manually enter Card ID
- [x] CSV contains correct Card ID and License Plate
- [x] Check-in validation requires capture
- [x] Status messages are clear
- [x] Table updates correctly
- [x] No data corruption in CSV

---

## 🎯 Workflow Now Correct

```
BEFORE (WRONG):
Video Capture → OCR Extract → AUTO-FILL Card ID → Check-in
                              ✗ Card ID = License Plate (Wrong!)

AFTER (CORRECT):
Video Capture → OCR Extract → Show License Plate in Purple Box
                              Operator Enters Card ID Manually → Check-in
                                                                ✓ Separate values
                                                                ✓ Correct CSV record
```

---

## 🚀 Next Steps

### Immediate Use
1. Deploy updated main_parking.py
2. Operators capture license plates
3. Operators enter card IDs manually
4. Check-in completes with both values

### Future Enhancements
- [ ] Barcode scanner for Card ID (auto-fill from barcode, not OCR)
- [ ] Duplicate license plate warning
- [ ] Multi-language support (Vietnamese/English)
- [ ] Sound notification on capture success

---

## 📞 Troubleshooting

### Snapshot Not Showing
- Check YOLO detection is working
- Verify camera frame quality
- Ensure license plate is visible in frame

### License Plate Text Not Displaying
- Check OCR model is loaded
- Verify image is clear enough
- Try better lighting conditions

### Check-in Fails
- Ensure license plate is captured first
- Check Card ID and Slot are not empty
- Verify no duplicate check-in exists

---

## 💾 NEW: Snapshot Storage Feature (v3.2.2)

### Automatic Snapshot Saving

When capturing license plates, the system now automatically saves snapshots:

**Folder:** `/home/lha20/draftK/captured_images/`

**Filename Format:** `plate_capture_YYYYMMDD_HHMMSS_mmm.jpg`

**Example:** `plate_capture_20260112_143045_123.jpg`

**Features:**
- ✅ Automatically creates folder if missing
- ✅ Unique filename with timestamp
- ✅ Only cropped license plate area saved (not full frame)
- ✅ JPEG format (compressed, ~900 KB per image)
- ✅ Continues working even if save fails

### Use Cases
1. **Verification** - Verify OCR extraction accuracy
2. **Dispute Resolution** - Review actual vehicle image
3. **Fraud Prevention** - Check for stolen plates
4. **Analytics** - Analyze vehicle types and patterns

### Storage Management
```bash
# List all snapshots
ls -la /home/lha20/draftK/captured_images/

# Count total captures
ls -1 /home/lha20/draftK/captured_images/ | wc -l

# Backup to external drive
cp -r /home/lha20/draftK/captured_images /mnt/backup/
```

### Storage Estimation
- Per capture: ~900 KB
- Per day (100 captures): ~90 MB
- Per month (3,000 captures): ~2.7 GB
- Per year (36,000 captures): ~32 GB

**Recommendation:** Archive old snapshots monthly to prevent running out of disk space.

---

**🔧 Snapshot & License Plate Extraction v3.2.2**  
**Status: ✅ Production Ready**  
**Date: January 12, 2026**

═════════════════════════════════════════════════════════════════════════════
