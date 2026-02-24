# 🅿️ Installation & Setup Guide - Parking Management System

**Version:** 3.0  
**Date:** February 24, 2026

---

## 📦 Installation Steps

### Step 0: Clone repo 
```bash

git clone https://github.com/LHA20/draftK.git

cd ~/draftK

git submodule update --init --recursive

cd

```

### Step 1: Navigate to Project Directory
```bash
cd ~/draftK
```

### Step 2: Create and Activate Virtual Environment
```bash

#Ubuntu/Linux:

python3 -m venv venv

source venv/bin/activate

#Window:
python3 -m venv venv

venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt

```

### Step 4: Verify Setup
```bash
python3 verify_setup.py
```

Expected output:
```
======================================================================
🚗 PARKING MANAGEMENT SYSTEM - SETUP VERIFICATION
======================================================================

Checking Python version... ✓ Python 3.10

Checking required packages:
  PyQt5        ✓
  OpenCV       ✓
  NumPy        ✓
  YOLO         ✓
  EasyOCR      ✓
  Pillow       ✓

Checking YOLO model file... ✓ Found (6.0 MB)

Checking directories:
  captured_images ✓
  YOLO Models     ✓

Checking camera access... ✓ OpenCV loaded

======================================================================
VERIFICATION SUMMARY
======================================================================
  Python Version            ✓ PASS
  Required Packages         ✓ PASS
  YOLO Model                ✓ PASS
  Directories               ✓ PASS
  Camera Access             ✓ PASS

Result: 5/5 checks passed

✓ ✓ ✓  All systems ready!  ✓ ✓ ✓

You can now run:
  python3 main_parking.py
```

---

## 🚀 Running the Application

### Direct Terminal
```bash
cd ~/draftK
source venv/bin/activate
python3 main_parking.py
```



## 📋 Requirements Summary

### Python Packages
- **PyQt5** 5.15.9 - GUI Framework
- **OpenCV** 4.8.0.74 - Image processing
- **YOLO (ultralytics)** 8.0.238 - License plate detection
- **EasyOCR** 1.6.2 - Text recognition
- **NumPy** 1.24.3 - Numerical computing
- **Pillow** 10.0.0 - Image handling
- **PyTorch** 2.9.1 - Deep learning backend
- **openpyxl** 3.1.5 - Excel export

### System Requirements
- **OS:** Linux (Ubuntu/Debian)
- **Python:** 3.7+ (3.10 recommended)
- **RAM:** 4 GB minimum, 8 GB recommended
- **Storage:** 500 MB free space
- **Camera:** USB or built-in camera
- **Display:** X11 or Wayland

---


## 📁 Project Structure

```
/home/lha20/draftK/
├── main_parking.py                    (Main application file)
├── requirements.txt                   (Python dependencies)
├── verify_setup.py                    (Setup verification script)
├── parking_records.csv                (Auto-created: vehicle records)
│
├── 📚 DOCUMENTATION:
├── PARKING_MANAGEMENT_GUIDE.md        (User guide)
├── GETTING_STARTED.md                 (Quick start)
├── README.md                          (Overview)
├── TROUBLESHOOTING.md                 (Problem solving)
│
├── 📁 DATA DIRECTORIES:
├── captured_images/                   (License plate photos)
│   ├── original_*.png
│   └── detected_*.png
│
├── 📁 YOLO MODEL:
├── Automatic-License-Plate-Recognition-using-YOLOv8/
│   └── license_plate_detector.pt      (6 MB YOLO model)
│
└── 📁 VIRTUAL ENVIRONMENT:
    └── venv/                          (Python packages)
```

---

## ✅ Configuration Checklist

### Before First Use
- [ ] Python 3.7+ installed
- [ ] Virtual environment created
- [ ] All packages installed
- [ ] Camera device accessible
- [ ] YOLO model file present (6 MB)
- [ ] CSV file will auto-create
- [ ] Excel export library installed

### Camera Setup
```bash
# Check camera device
ls -la /dev/video*

# If camera not accessible:
sudo usermod -a -G video $USER
# Then restart your system
```

### YOLO Model File
```bash
# Verify model exists
ls -lh ~/draftK/Automatic-License-Plate-Recognition-using-YOLOv8/license_plate_detector.pt

# Should show: -rw-r--r-- 1 user user 6.0M ...
```

---

## 🧪 Quick Test

After installation, run this simple test:

```bash
cd ~/draftK
source venv/bin/activate

python3 -c "
print('Testing imports...')
from PyQt5.QtWidgets import QApplication
print('✓ PyQt5')

import cv2
print('✓ OpenCV')

import numpy as np
print('✓ NumPy')

from ultralytics import YOLO
print('✓ YOLO')

import easyocr
print('✓ EasyOCR')

import openpyxl
print('✓ openpyxl')

print('\n✅ All components working!')
"
```

---

## 🆘 Common Installation Issues

### Issue 1: "No module named 'PyQt5'"
```bash
pip install PyQt5==5.15.9
```

### Issue 2: "No module named 'ultralytics'"
```bash
pip install ultralytics==8.0.238
```

### Issue 3: "No module named 'easyocr'"
```bash
pip install easyocr==1.6.2
```

### Issue 4: "Cannot load YOLO model"
```bash
# Check if model file exists
ls -lh Automatic-License-Plate-Recognition-using-YOLOv8/license_plate_detector.pt

# If missing, download or train model
# See: https://github.com/Muhammad-Zeerak-Khan/Automatic-License-Plate-Recognition-using-YOLOv8
```

### Issue 5: "Camera not working"
```bash
# Grant camera permissions
sudo usermod -a -G video $USER

# Log out and back in, then test:
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Failed'); cap.release()"
```

### Issue 6: "Excel export fails"
```bash
pip install openpyxl==3.1.5
```

### Issue 7: "Qt platform plugin error"
```bash
export QT_QPA_PLATFORM=offscreen
python3 main_parking.py
```

---

## 📝 Environment Variables (Optional)

For advanced users:

```bash
# Use offscreen rendering (for servers)
export QT_QPA_PLATFORM=offscreen

# Disable CUDA (force CPU)
export CUDA_VISIBLE_DEVICES=-1

# Set log level
export TF_CPP_MIN_LOG_LEVEL=2
```

---

## 🐍 Python Version Check

Make sure you have Python 3.7 or higher:

```bash
python3 --version
# Output: Python 3.10.x

# If you need to install Python 3.10:
sudo apt update
sudo apt install python3.10 python3.10-venv
```

---

## 🔄 Updating Dependencies

To update all packages to latest versions:

```bash
cd ~/draftK
source venv/bin/activate

pip install --upgrade -r requirements.txt
pip install --upgrade openpyxl
```

---

## 🗑️ Cleaning Up

To remove all virtual environment and start fresh:

```bash
cd ~/draftK

# Remove virtual environment
rm -rf venv

# Recreate from scratch
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install openpyxl
```

---

## 📊 Disk Space Usage

Typical installation requires:

| Component | Size |
|-----------|------|
| Python venv | ~300 MB |
| YOLO model | ~6 MB |
| EasyOCR models | ~100 MB |
| OpenCV | ~50 MB |
| Dependencies | ~400 MB |
| **Total** | **~860 MB** |

---

## ⚡ Performance Tips

### For Better Performance:
1. Close unnecessary applications
2. Use SSD for faster model loading
3. 4GB+ RAM recommended
4. Dual-core CPU minimum

### GPU Acceleration (Optional):
If you have an NVIDIA GPU:
```bash
# Install CUDA version of PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 🆘 Getting Help

### 1. Check Setup
```bash
python3 verify_setup.py
```

### 2. Check Logs
```bash
cat /tmp/parking.log
```

### 3. Review Documentation
- `PARKING_MANAGEMENT_GUIDE.md` - User guide
- `TROUBLESHOOTING.md` - Common issues
- `GETTING_STARTED.md` - Quick start

### 4. Test Components
```bash
python3 test_components.py
```

---

## ✨ You're Ready!

Once setup is complete, launch the application:

```bash
cd ~/draftK
source venv/bin/activate
python3 main_parking.py
```

The Parking Management System will:
- ✅ Load YOLO model
- ✅ Initialize camera
- ✅ Open user interface
- ✅ Be ready for vehicle check-in/out

---

**Happy parking management! 🅿️**

**Version:** 3.0  
**Status:** ✅ Installation Complete  
**Date:** January 12, 2026
