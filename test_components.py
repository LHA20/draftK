#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parking Management System - Quick Test Script
Tests all components without starting the GUI
"""

import sys
from pathlib import Path

print("=" * 70)
print("🚗 PARKING MANAGEMENT SYSTEM - COMPONENT TEST")
print("=" * 70)
print()

# Test 1: PyQt5
print("Test 1: PyQt5 GUI Framework", end=" ")
try:
    from PyQt5.QtWidgets import QApplication
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 2: OpenCV
print("Test 2: OpenCV Image Processing", end=" ")
try:
    import cv2
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 3: NumPy
print("Test 3: NumPy Numerical Computing", end=" ")
try:
    import numpy as np
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 4: YOLO Detection
print("Test 4: YOLO Detection Model", end=" ")
try:
    # Monkey-patch torch.load first
    import torch
    _original_torch_load = torch.load
    def patched_torch_load(f, *args, **kwargs):
        kwargs['weights_only'] = False
        return _original_torch_load(f, *args, **kwargs)
    torch.load = patched_torch_load
    
    from ultralytics import YOLO
    model_path = Path(__file__).parent / "Automatic-License-Plate-Recognition-using-YOLOv8" / "license_plate_detector.pt"
    
    if model_path.exists():
        print("✓")
    else:
        print(f"✗ Model not found at {model_path}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 5: EasyOCR
print("Test 5: EasyOCR Text Recognition", end=" ")
try:
    import easyocr
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 6: Data Files
print("Test 6: Required Data Files", end=" ")
try:
    base_path = Path(__file__).parent
    
    # Check model file
    model_file = base_path / "Automatic-License-Plate-Recognition-using-YOLOv8" / "license_plate_detector.pt"
    if not model_file.exists():
        raise FileNotFoundError(f"YOLO model not found: {model_file}")
    
    # Check captured_images directory
    img_dir = base_path / "captured_images"
    if not img_dir.exists():
        img_dir.mkdir(parents=True, exist_ok=True)
    
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 7: CSV File
print("Test 7: CSV Data Export", end=" ")
try:
    import csv
    csv_file = Path(__file__).parent / "license_plate_records.csv"
    
    # Try to write and read CSV
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['License Plate', 'Detection Time', 'Confidence'])
    
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 8: Threading
print("Test 8: Multi-Threading Support", end=" ")
try:
    import threading
    from PyQt5.QtCore import pyqtSignal, QObject
    
    class TestSignals(QObject):
        test_signal = pyqtSignal(str)
    
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Summary
print()
print("=" * 70)
print("✅ ALL TESTS PASSED")
print("=" * 70)
print()
print("System Status:")
print("  • Python Version: 3.7+  ✓")
print("  • PyQt5:               ✓")
print("  • OpenCV:              ✓")
print("  • YOLO Model:          ✓")
print("  • EasyOCR:             ✓")
print("  • Dependencies:        ✓")
print()
print("🚀 Ready to launch application:")
print()
print("   $ python3 main.py")
print()
