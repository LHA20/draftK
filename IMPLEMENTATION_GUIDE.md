#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PARKING MANAGEMENT SYSTEM - IMPLEMENTATION GUIDE
License Plate Recognition with YOLO and OCR

This document explains the integration of:
1. YOLO license plate detection
2. EasyOCR text recognition
3. PyQt5 user interface
4. Real-time frame processing
"""

# ============================================================================
# PROJECT STRUCTURE
# ============================================================================

"""
draftK/
├── main.py                                          # Main application
│   ├── CameraSignals                               # PyQt signals class
│   ├── CameraWorker                                # Camera thread worker
│   ├── ParkingManagementSystem                     # Main UI window
│   └── Helper functions (OCR, format validation)
│
├── Automatic-License-Plate-Recognition-using-YOLOv8/
│   ├── license_plate_detector.pt                   # Pre-trained YOLO model
│   ├── util.py                                     # Original utility functions
│   └── sort.py                                     # Vehicle tracking
│
├── requirements.txt                                # Python dependencies
├── install.sh                                      # Setup script
├── run.sh                                          # Launch script
├── README.md                                       # User documentation
├── IMPLEMENTATION_GUIDE.md                         # This file
│
├── captured_images/                                # Output: saved frames
└── license_plate_records.csv                       # Output: detection log
"""

# ============================================================================
# KEY COMPONENTS
# ============================================================================

"""
1. OCR PROCESSING PIPELINE
   ─────────────────────────
   
   Raw Camera Frame
   ↓
   YOLO License Plate Detection
   ↓
   Extract Bounding Box
   ↓
   Crop License Plate Region
   ↓
   Convert to Grayscale
   ↓
   Binary Threshold
   ↓
   EasyOCR Text Recognition
   ↓
   Character Format Correction (O→0, I→1, etc.)
   ↓
   License Format Validation
   ↓
   Store Detection Record
   ↓
   Display in Table + Save to CSV

2. YOLO DETECTION
   ───────────────
   - Model: license_plate_detector.pt (trained on license plate dataset)
   - Input: Full frame (1280x720)
   - Output: Bounding boxes with confidence scores
   - Speed: ~30ms per frame on CPU

3. OCR RECOGNITION
   ────────────────
   - Engine: EasyOCR with English language model
   - Input: Grayscale, thresholded license plate crop
   - Output: Text string with confidence score
   - Processing: On-demand (only for detected regions)

4. CHARACTER CORRECTION
   ────────────────────
   Maps common OCR errors:
   O → 0 (letter O to digit zero)
   I → 1 (letter I to digit one)
   J → 3 (letter J to digit three)
   A → 4 (letter A to digit four)
   G → 6 (letter G to digit six)
   S → 5 (letter S to digit five)

5. FORMAT VALIDATION
   ──────────────────
   Expected format: AA9999A (2 letters + 4 digits + 1 letter)
   
   Examples of valid formats:
   - AB1234C (standard)
   - XY5678Z (standard)
   - AB0000A (edge case)
   
   Invalid formats are rejected:
   - ABC1234 (too many letters at start)
   - AB12C (insufficient digits)
   - 1234ABC (starts with digit)
"""

# ============================================================================
# THREADING MODEL
# ============================================================================

"""
Main Thread (PyQt Event Loop)
├── User Interface Updates
├── Button Click Handlers
└── Signal Processing

Camera Worker Thread (independent)
├── Continuous camera capture
├── YOLO detection (non-blocking)
├── Emit frame_ready signal
└── Emit license_detected signal

This architecture ensures:
- Smooth UI responsiveness
- Non-blocking video processing
- Real-time frame display
- Concurrent detection and display
"""

# ============================================================================
# SIGNAL FLOW
# ============================================================================

"""
CameraWorker (Thread) ──┐
                        ├─→ frame_ready signal ──→ on_frame_received()
    • Capture frame     │     - Display camera feed
    • Run YOLO          │     - Draw detection boxes
    • Extract license   │
                        ├─→ license_detected signal ──→ on_license_detected()
                        │     - Update table
                        │     - Save to CSV
                        │     - Update status
                        │
                        └─→ error_signal ──→ on_camera_error()
                             - Display error message
"""

# ============================================================================
# KEY FUNCTIONS EXPLAINED
# ============================================================================

"""
1. check_license_format(text: str) → bool
   
   Purpose: Validate if detected text matches license plate format
   
   Logic:
   - Check length == 7
   - Char[0-1]: Letters (or mapped numerals)
   - Char[2-5]: Numbers (or mapped letters)
   - Char[6]: Letter (or mapped numeral)
   
   Example:
   >>> check_license_format("AB1234C")
   True
   >>> check_license_format("ABCDEFG")
   False

2. format_license_plate(text: str) → str
   
   Purpose: Correct common OCR errors using mapping
   
   Logic:
   - Use position-specific mappings
   - First 2 chars: map digits to letters
   - Middle 4 chars: map letters to digits
   - Last char: map digits to letters
   
   Example:
   >>> format_license_plate("ABI234C")  # OCR read I instead of 1
   "AB1234C"

3. extract_license_plate(crop: ndarray) → tuple
   
   Purpose: Run OCR and return validated license text
   
   Logic:
   1. Send image to EasyOCR
   2. Extract text and confidence
   3. Clean up (uppercase, remove spaces)
   4. Validate format
   5. Apply character mapping
   6. Return formatted text and score
   
   Returns: (license_text, confidence_score) or (None, None)

4. CameraWorker.run()
   
   Purpose: Main camera capture and detection loop
   
   Steps:
   1. Initialize camera (1280x720, 30 FPS)
   2. Main loop:
      a. Capture frame
      b. Run YOLO detection
      c. For each detection:
         - Draw bounding box
         - Crop license plate region
         - Convert to grayscale and threshold
         - Run OCR
         - Emit license_detected signal if successful
      d. Emit frame_ready signal with annotated frame
   3. Release resources on exit

5. ParkingManagementSystem.on_license_detected()
   
   Purpose: Handle new license plate detection
   
   Steps:
   1. Get current timestamp
   2. Check if it's a duplicate (within 2 seconds)
   3. Add to detection history
   4. Add record to license_records list
   5. Update table widget
   6. Save to CSV
   7. Update status label

6. ParkingManagementSystem.capture_image()
   
   Purpose: Save current frame with metadata
   
   Steps:
   1. Get current frame from camera worker
   2. Create timestamp-based filename
   3. Save frame using cv2.imwrite()
   4. Display preview in UI
   5. Save metadata to CSV
   6. Update status message
"""

# ============================================================================
# DATA STRUCTURES
# ============================================================================

"""
License Record Format
──────────────────────

List item:
{
    'license': 'AB1234C',           # Recognized license plate text
    'time': '2026-01-11 14:30:25',  # Detection timestamp
    'confidence': 0.95              # OCR confidence score
}

CSV Record:
License Plate,Detection Time,Confidence
AB1234C,2026-01-11 14:30:25,0.95
XY5678Z,2026-01-11 14:31:45,0.92

Detection History (for deduplication):
{
    'AB1234C': datetime(2026, 1, 11, 14, 30, 25),
    'XY5678Z': datetime(2026, 1, 11, 14, 31, 45)
}
"""

# ============================================================================
# PERFORMANCE OPTIMIZATION TIPS
# ============================================================================

"""
1. Reduce YOLO Inference Time
   - Use YOLOv8n (nano) instead of larger models
   - Lower input resolution: 640x480 instead of 1280x720
   - Process every Nth frame instead of every frame
   
   Example:
   if frame_count % 3 == 0:  # Process every 3rd frame
       detections = detector(frame)

2. Optimize OCR Processing
   - Process only detected regions (already done)
   - Use lower resolution crops
   - Cache model between detections
   
3. Reduce UI Update Frequency
   - Update table only for new detections
   - Display frames at 15-20 FPS instead of 30
   
4. Hardware Acceleration
   - Enable CUDA if NVIDIA GPU available
   - Use mobile-optimized models

5. Memory Management
   - Clear frame buffer regularly
   - Use generator pattern for large datasets
   - Release resources in worker thread cleanup
"""

# ============================================================================
# TROUBLESHOOTING GUIDE
# ============================================================================

"""
1. YOLO Model Not Found
   Error: "license_plate_detector.pt not found"
   Solution:
   - Check file location: Automatic-License-Plate-Recognition-using-YOLOv8/
   - Verify model_path is correct in ParkingManagementSystem.__init__
   - Download model if missing

2. No License Plates Detected
   Causes:
   - Low camera resolution
   - Poor lighting
   - Model not loading properly
   - Confidence threshold too high
   
   Solutions:
   - Improve lighting conditions
   - Test YOLO separately: python3 -c "from ultralytics import YOLO; m=YOLO('model.pt')"
   - Lower confidence threshold in detection loop

3. OCR Recognition Failures
   Causes:
   - Image quality too low
   - Threshold not optimal for specific plates
   - Model language mismatch
   
   Solutions:
   - Adjust threshold values in CameraWorker.run():
     _, lp_thresh = cv2.threshold(lp_gray, 64, 255, cv2.THRESH_BINARY_INV)
   - Use cv2.morphologyEx for preprocessing
   - Try different OCR backends

4. High False Positives (wrong detections)
   Solutions:
   - Increase confidence threshold
   - Add license format validation (already done)
   - Implement confidence filtering

5. Memory Usage Increasing
   Causes:
   - Memory leak in frame processing
   - Unbounded detection history growth
   
   Solutions:
   - Clear detection history periodically
   - Implement frame buffer size limit
   - Profile with memory_profiler

6. Slow Frame Display
   Causes:
   - UI update blocked by YOLO processing
   - Inefficient frame conversion
   
   Solutions:
   - Already using threading
   - Optimize cv2.cvtColor with optimized=True
   - Pre-allocate arrays
"""

# ============================================================================
# CONFIGURATION REFERENCE
# ============================================================================

"""
Camera Configuration (in CameraWorker.__init__)
─────────────────────
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS = 30

License Format (in check_license_format)
─────────────────────
Format: AA9999A
Length: 7 characters
Positions: [0-1: letters, 2-5: numbers, 6: letter]

Deduplication Window (in on_license_detected)
─────────────────────
TIME_WINDOW = 2 seconds (minimum between same plate detections)

Threshold Settings (in CameraWorker.run)
─────────────────────
THRESHOLD_VALUE = 64
BINARY_METHOD = cv2.THRESH_BINARY_INV

OCR Configuration (global)
─────────────────────
LANGUAGE = 'en' (English)
GPU = False (set to True if CUDA available)
"""

# ============================================================================
# INTEGRATION WITH REFERENCE PROJECT
# ============================================================================

"""
Original Reference (Automatic-License-Plate-Recognition-using-YOLOv8):
───────────────────────────────────────────────────────────────────
- Processed video files
- Used vehicle tracking (SORT algorithm)
- Wrote results to CSV

Parking Management System Adaptations:
──────────────────────────────────────
✗ Removed: Video file processing (now uses live camera)
✗ Removed: Vehicle tracking (focus on plates only)
✗ Removed: Tracking IDs (not needed for parking)

✓ Added: Real-time UI with PyQt5
✓ Added: Live table display
✓ Added: Image capture functionality
✓ Added: Threading for non-blocking UI
✓ Added: Deduplication of detections
✓ Added: Confidence scoring in CSV
✓ Enhanced: Format validation
✓ Enhanced: Character correction mapping
"""

# ============================================================================
# FUTURE ENHANCEMENTS
# ============================================================================

"""
Potential Features for Version 3.0:

1. Vehicle Tracking
   - Implement SORT or Deep SORT
   - Track vehicles across frames
   - Estimate direction of travel

2. Multi-Camera Support
   - Handle multiple camera feeds
   - Synchronize across cameras
   - Detect same vehicle in multiple cameras

3. Database Integration
   - Replace CSV with SQLite/PostgreSQL
   - Query historical data
   - Generate reports

4. Web Dashboard
   - Flask/Django backend
   - Real-time detection feed
   - Remote monitoring

5. Advanced Reporting
   - Daily/weekly statistics
   - Frequently seen plates
   - Unknown plates (non-matching format)

6. Machine Learning
   - Custom license plate trainer
   - Region-specific format support
   - Confidence threshold optimization

7. Integration Features
   - Gate control (open/close)
   - License plate whitelist/blacklist
   - Alert system for flagged vehicles

8. Performance Improvements
   - GPU acceleration with CUDA
   - Model quantization
   - Batched inference
   - Edge device deployment (Jetson Nano)
"""

# ============================================================================
# TESTING CHECKLIST
# ============================================================================

"""
Before deployment, verify:

□ Camera initialization
  □ Default camera (index 0) works
  □ Alternative camera indices if needed
  □ Resolution and FPS settings correct

□ YOLO Detection
  □ Model loads successfully
  □ Detections display with bounding boxes
  □ Confidence scores reasonable

□ OCR Recognition
  □ Text extraction works on cropped images
  □ Character mapping applies correctly
  □ Format validation works for valid/invalid inputs

□ UI Components
  □ Camera feed displays smoothly
  □ Table updates with new detections
  □ Image preview updates on capture
  □ Status label shows current state

□ Data Persistence
  □ CSV file creates automatically
  □ Records append without error
  □ Images save to correct directory
  □ Duplicate detection prevention works

□ Error Handling
  □ Missing model handled gracefully
  □ Camera not available handled
  □ OCR failures don't crash app
  □ CSV write errors caught

□ Performance
  □ Frame rate >= 15 FPS
  □ UI responsive to clicks
  □ No memory leaks over time
  □ CPU usage reasonable

□ Documentation
  □ All functions have docstrings
  □ Comments explain complex logic
  □ README accurate and complete
  □ Code follows PEP 8 style
"""

# ============================================================================
# END OF IMPLEMENTATION GUIDE
# ============================================================================
