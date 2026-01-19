# � Parking Management System - License Plate Recognition

Advanced parking management software with real-time YOLO-based license plate detection and OCR-powered character recognition.

## 🎯 Features

### Core Functionality
- ✅ **Real-Time Camera Feed**: Live video display from webcam with YOLO license plate detection
- ✅ **YOLO Detection**: Automatic bounding box visualization of detected license plates
- ✅ **OCR Recognition**: Intelligent character recognition using EasyOCR
- ✅ **License Plate Extraction**: Automatic extraction of plate text from cropped images
- ✅ **Image Capture**: Capture frames with detected license plates
- ✅ **License Plate Records**: Maintain a table of detected license plates with timestamps
- ✅ **CSV Export**: Automatic logging of all detections to CSV file

### User Interface
- Split-panel design: Live video feed (left), controls & records table (right)
- Real-time YOLO detection boxes overlay on camera feed
- Scrollable table displaying license plate data
- Last captured image preview
- Status indicators for camera and detection status

## 📋 Requirements

### System Requirements
- Python 3.7 or higher
- Functional webcam/camera device
- Linux, macOS, or Windows
- GPU (optional, for faster processing)

### Software Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| PyQt5 | 5.15.9 | User interface |
| opencv-python-headless | 4.8.1.78 | Video processing |
| ultralytics | 8.0.238 | YOLO models |
| easyocr | 1.6.2 | OCR text recognition |
| numpy | 1.24.3 | Array processing |
| Pillow | 10.0.0 | Image manipulation |

## 🚀 Installation

### Step 1: Setup Python Environment

```bash
cd /home/lha20/draftK
```

### Step 2: Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows
```

### Step 3: Install Dependencies

**Option A: Using install script**
```bash
chmod +x install.sh
./install.sh
```

**Option B: Manual installation**
```bash
pip install -r requirements.txt
```

### Step 4: Prepare YOLO Models

The system expects a pre-trained license plate detector model at:
```
/home/lha20/draftK/Automatic-License-Plate-Recognition-using-YOLOv8/license_plate_detector.pt
```

If you don't have the model file, you can:
1. Train your own YOLO model on license plate dataset
2. Download a pre-trained model from the Automatic-License-Plate-Recognition repository

## 🎮 Usage

### Launch Application

```bash
source venv/bin/activate
python3 main.py
```

Or use the run script:
```bash
chmod +x run.sh
./run.sh
```

### Operating the System

1. **Start**: Application initializes and begins capturing camera feed
2. **Auto-Detection**: YOLO automatically detects license plates in real-time
3. **View Records**: Detected plates appear in the table with timestamps
4. **Capture Frame**: Click "CAPTURE IMAGE" to save current frame with overlays
5. **Export Data**: Records are automatically saved to `license_plate_records.csv`

## 📁 Project Structure

```
draftK/
├── main.py                                    # Main application
├── requirements.txt                           # Python dependencies
├── install.sh                                 # Setup script
├── run.sh                                     # Launch script
├── README.md                                  # This file
├── TROUBLESHOOTING.md                         # Troubleshooting guide
├── license_plate_records.csv                  # Auto-generated records
├── captured_images/                           # Saved captured frames
└── Automatic-License-Plate-Recognition-using-YOLOv8/
    ├── license_plate_detector.pt              # YOLO model file
    ├── util.py                                # Utility functions
    └── sort.py                                # Sort tracker
```

## � Configuration

### Camera Settings
The application automatically configures the camera with:
- Resolution: 1280x720
- FPS: 30
- Auto-flip: Enabled (horizontal flip for comfort)

To modify these settings, edit the `CameraWorker.run()` method in `main.py`:

```python
self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
self.cap.set(cv2.CAP_PROP_FPS, 30)
```

### License Plate Format
The default format expects:
- 2 letters + 4 numbers + 1 letter (e.g., AB1234C)

Modify in `check_license_format()` function to match your region's format.

## 📊 Data Management

### CSV Records
Detected plates are automatically logged to `license_plate_records.csv` with:
- License Plate number
- Detection timestamp
- Confidence score

Example:
```csv
License Plate,Detection Time,Confidence
AB1234C,2026-01-11 14:30:25,0.95
XY5678Z,2026-01-11 14:31:45,0.92
```

### Image Capture
Captured frames are saved to `captured_images/` directory with naming:
- Format: `capture_YYYYMMDD_HHMMSS.png`
- Example: `capture_20260111_143025.png`

## 🐛 Troubleshooting

### Camera Issues
See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

**Common Issues:**
- Cannot open camera: Check `/dev/video*` permissions
- Low FPS: Reduce resolution or disable other applications
- YOLO model not found: Verify model path and file exists

### OCR Issues
- Poor recognition: Improve image quality, adjust threshold in `CameraWorker.run()`
- No plates detected: Check YOLO model loading in `CameraWorker.__init__()`

## 🔍 Technical Details

### YOLO Detection Pipeline
1. Capture frame from camera
2. Pass to YOLO detector
3. Extract bounding boxes for plates
4. Crop plate regions
5. Convert to grayscale and threshold
6. Pass to OCR for text extraction

### OCR Processing
1. Read cropped license plate image
2. Extract text using EasyOCR
3. Format text (replace O→0, I→1, etc.)
4. Validate against license format
5. Return recognized text with confidence

## 📝 Code Comments

All source code includes detailed English comments explaining:
- Function purposes
- Parameter descriptions
- Return value formats
- Processing steps

## 👨‍💻 Development

### Adding Custom Features

**Example: Save detected plates with images**

```python
def save_detection_record(self, license_text, frame, timestamp):
    """Save detection along with captured image"""
    filename = f"{license_text}_{timestamp}.png"
    cv2.imwrite(str(self.image_dir / filename), frame)
```

### Performance Optimization

For faster processing on low-end hardware:
1. Reduce camera resolution: 640x480 instead of 1280x720
2. Lower FPS: 15 instead of 30
3. Use lightweight YOLO: YOLOv8n instead of larger models
4. Disable redundant checks in detection loop

## 📄 License

This project builds upon:
- [Automatic-License-Plate-Recognition-using-YOLOv8](https://github.com/path/to/repo)
- Ultralytics YOLO
- PyQt5
- EasyOCR

See individual packages for their respective licenses.

## � Support

For issues or questions:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review code comments in `main.py`
3. Examine console output for error messages
4. Verify model files and camera permissions

---

**Version**: 2.0 (Enhanced with License Plate Recognition)  
**Last Updated**: January 11, 2026  
**Status**: Production Ready
