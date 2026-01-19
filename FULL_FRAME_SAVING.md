# 📸 Full Frame Saving Feature - Version 3.2.2

**Date:** January 12, 2026  
**Feature:** Save complete video frame (full screenshot) when capturing license plate  
**Status:** ✅ **IMPLEMENTED & TESTED**

---

## 🎯 What Changed

### Previous Behavior (v3.1)
- Only saved **cropped license plate area** (~30-40KB per image)
- Filename: `plate_capture_20260112_234706_215.jpg`
- Could not verify full context of where vehicle was parked

### New Behavior (v3.2.2)
- Saves **FULL VIDEO FRAME** (entire screenshot) (~200-900KB per image)
- Also saves **cropped license plate** for reference
- Filenames:
  - Full frame: `full_frame_20260112_235041.jpg`
  - License plate crop: `license_plate_20260112_235041.jpg`
- Users can verify vehicle position, lighting, parking area, etc.

---

## 💾 Image Storage

### Folder Structure
```
/home/lha20/draftK/
└── captured_images/
    ├── full_frame_20260112_235041.jpg       ← Full screenshot (~500KB)
    ├── license_plate_20260112_235041.jpg    ← Crop only (~35KB)
    ├── full_frame_20260112_235100.jpg
    ├── license_plate_20260112_235100.jpg
    ├── ... (more captures)
    └── [Old PNG files from previous version]
```

### File Naming
```
full_frame_YYYYMMDD_HHMMSS_mmm.jpg
  YYYY = Year (2026)
  MM = Month (01)
  DD = Day (12)
  HH = Hour (23)
  MM = Minute (50)
  SS = Second (41)
  mmm = Milliseconds (791)

license_plate_YYYYMMDD_HHMMSS_mmm.jpg
  Same timestamp as full frame
```

### File Sizes
| Type | Size | Purpose |
|------|------|---------|
| Full Frame | 200-900 KB | Complete video capture, context verification |
| License Plate Crop | 20-50 KB | Just the plate area for OCR |
| Total per capture | ~250-950 KB | Both images stored |

---

## 🔧 Code Implementation

### What Was Changed

**File:** `main_parking.py`  
**Function:** `capture_plate()`  
**Lines:** 608-625

### Before (Save Only Crop)
```python
# Save cropped image to captured_images folder
try:
    captured_dir = Path(__file__).parent / "captured_images"
    captured_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    snapshot_filename = f"plate_capture_{timestamp}.jpg"
    snapshot_path = captured_dir / snapshot_filename
    
    # Save ONLY the cropped image
    cv2.imwrite(str(snapshot_path), crop)
    print(f"✓ Snapshot saved: {snapshot_path}")
except Exception as save_error:
    print(f"Warning: Could not save snapshot: {save_error}")
```

### After (Save Full Frame + Crop)
```python
# Save FULL FRAME (entire video capture) to captured_images folder
try:
    captured_dir = Path(__file__).parent / "captured_images"
    captured_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    
    # Save FULL FRAME (entire screenshot with entire vehicle/parking area)
    full_frame_filename = f"full_frame_{timestamp}.jpg"
    full_frame_path = captured_dir / full_frame_filename
    cv2.imwrite(str(full_frame_path), self.current_frame)
    print(f"✓ Full frame saved: {full_frame_path}")
    
    # Also save cropped license plate (for reference/verification)
    crop_filename = f"license_plate_{timestamp}.jpg"
    crop_path = captured_dir / crop_filename
    cv2.imwrite(str(crop_path), crop)
    print(f"✓ License plate crop saved: {crop_path}")
except Exception as save_error:
    print(f"Warning: Could not save images: {save_error}")
```

---

## 📊 Benefits

### For Operators
✅ **Verify Vehicle Location:** See exactly where the vehicle is parked  
✅ **Check Lighting Conditions:** Verify image quality and visibility  
✅ **Audit Trail:** Complete visual record of each transaction  
✅ **Dispute Resolution:** Have evidence of vehicle position and condition  

### For Managers
✅ **Insurance Claims:** Full frame for evidence if accident or dispute  
✅ **Traffic Flow:** Understand parking patterns and vehicle movements  
✅ **Quality Assurance:** Verify operators are capturing correct vehicles  
✅ **Investigation:** Review full context if issues occur  

### For IT
✅ **Better Debugging:** Full context when troubleshooting OCR  
✅ **Training Data:** Actual vehicle photos for improving OCR models  
✅ **Analytics:** Analyze lighting, angles, vehicle types  

---

## 📁 Storage Considerations

### Disk Space Estimation

**Per Capture:**
- Full frame: ~500 KB (average)
- License plate crop: ~35 KB (average)
- **Total: ~535 KB per capture pair**

**Daily Usage (Example):**
- 200 vehicles per day
- 200 captures per day
- **Storage: 200 × 535 KB = ~107 MB per day**
- **Monthly: ~3.2 GB per month**

### Cleanup Recommendations

**Option 1: Automatic Cleanup**
```python
# Keep only last 30 days
import os
from datetime import datetime, timedelta

images_dir = Path(__file__).parent / "captured_images"
cutoff_date = datetime.now() - timedelta(days=30)

for file in images_dir.glob("*.jpg"):
    file_time = datetime.fromtimestamp(file.stat().st_mtime)
    if file_time < cutoff_date:
        file.unlink()
        print(f"Deleted old image: {file.name}")
```

**Option 2: Manual Cleanup**
```bash
# Remove images older than 30 days
find /home/lha20/draftK/captured_images/ -name "*.jpg" -mtime +30 -delete

# Archive to external drive (recommended)
tar -czf parking_images_2026_01.tar.gz captured_images/
```

**Option 3: Change Capture Policy**
- Only save full frame for certain transactions (OUT only)
- Compress images to reduce size
- Use lower resolution/quality

---

## 🎯 Workflow

### When User Captures License Plate

```
User clicks "📸 CAPTURE LICENSE PLATE"
    ↓
System captures current video frame
    ↓
YOLO detects license plate location
    ↓
Extract plate area and OCR text
    ↓
SAVE FULL FRAME
    ├─ Save: full_frame_TIMESTAMP.jpg (complete video)
    ├─ Size: ~500 KB
    └─ Contains: entire parking area, vehicle, context
    ↓
SAVE CROPPED LICENSE PLATE
    ├─ Save: license_plate_TIMESTAMP.jpg (crop only)
    ├─ Size: ~35 KB
    └─ Contains: just the license plate
    ↓
Display full frame in snapshot area
    ↓
User enters Card ID and Slot Number
    ↓
User clicks "CHECK IN"
```

---

## ✅ Verification Checklist

- [x] Full frame saved to `captured_images` folder
- [x] License plate crop also saved
- [x] Unique timestamp for each capture
- [x] JPG format (compressed)
- [x] Both files have matching timestamp
- [x] Folder automatically created if missing
- [x] Error handling for save failures
- [x] Console logs for verification
- [x] No impact on OCR processing
- [x] No impact on UI responsiveness

---

## 📝 Console Output Example

When user captures a license plate, you'll see:

```
Loading OCR reader... ✓
======================================================================
🅿️  PARKING MANAGEMENT SYSTEM
======================================================================

✓ License plate detector model loaded
✓ Window displayed
✓ Application ready
✓ Camera initialized

[User clicks CAPTURE button]

✓ Full frame saved: /home/lha20/draftK/captured_images/full_frame_20260112_235041_791.jpg
✓ License plate crop saved: /home/lha20/draftK/captured_images/license_plate_20260112_235041_791.jpg

✅ License Plate Captured: ABC-XYZ-789 (Confidence: 85.23%)
```

---

## 🔍 How to View Saved Images

### Using File Manager
```bash
# Open folder
nautilus /home/lha20/draftK/captured_images/

# Or
xdg-open /home/lha20/draftK/captured_images/
```

### Using Command Line
```bash
# List all full frames
ls -lh /home/lha20/draftK/captured_images/full_frame_*.jpg

# List all crops
ls -lh /home/lha20/draftK/captured_images/license_plate_*.jpg

# View image info
identify /home/lha20/draftK/captured_images/full_frame_20260112_235041_791.jpg
```

### Using Python
```python
from pathlib import Path
from PIL import Image

images_dir = Path("/home/lha20/draftK/captured_images")

for img_file in sorted(images_dir.glob("full_frame_*.jpg")):
    img = Image.open(img_file)
    print(f"{img_file.name}: {img.size} ({img.format})")
```

---

## 🚀 How to Disable (Optional)

If you want to save only crops (to save space), modify the code:

```python
# Keep this (crop saved for verification)
crop_filename = f"license_plate_{timestamp}.jpg"
crop_path = captured_dir / crop_filename
cv2.imwrite(str(crop_path), crop)

# Remove this (don't save full frame)
# full_frame_filename = f"full_frame_{timestamp}.jpg"
# full_frame_path = captured_dir / full_frame_filename
# cv2.imwrite(str(full_frame_path), self.current_frame)
```

---

## 📊 Image Size Comparison

### Full Frame (1280×720)
```
Typical size: 500-900 KB
Quality: Full resolution
Content: Complete vehicle + parking area + background
Use: Context verification, audit trail
```

### License Plate Crop
```
Typical size: 20-50 KB
Quality: Cropped to plate only
Content: Just the license plate
Use: OCR input, quick reference
```

---

## 🔐 Security & Privacy

**Data Protection:**
- Images stored locally on server
- Not transmitted to cloud
- Accessible only to authorized users
- Recommend setting folder permissions:
  ```bash
  chmod 750 /home/lha20/draftK/captured_images/
  chown root:parking_managers /home/lha20/draftK/captured_images/
  ```

**GDPR/Privacy Compliance:**
- Images contain vehicle license plates (public info)
- Consider data retention policy (30-90 days recommended)
- Implement automatic cleanup for old images
- Document purpose: "Parking lot management & verification"

---

## 🎯 Version History

**v3.0** - Initial system  
**v3.1** - UI redesign  
**v3.2** - Excel export fix, full frame saving  
**v3.2.2** - ✅ **Current - Full frame saving**

---

## 📞 Support

### Issue: Images not being saved
```bash
# Check permissions
ls -ld /home/lha20/draftK/captured_images/

# Check disk space
df -h /home/lha20/draftK/

# Check if captures are happening
tail -20 /path/to/application/log.txt
```

### Issue: Too many images, storage full
```bash
# Check disk usage
du -sh /home/lha20/draftK/captured_images/

# Archive old images
tar -czf parking_images_jan.tar.gz captured_images/

# Delete old images (keep last 30 days)
find captured_images/ -name "*.jpg" -mtime +30 -delete
```

---

**📸 Full Frame Saving Feature**  
**Version:** 3.2.2  
**Status:** ✅ Complete & Tested  
**Date:** January 12, 2026

═════════════════════════════════════════════════════════════════════════════
