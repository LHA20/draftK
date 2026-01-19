#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parking Management System - Headless Test Mode
Tests YOLO and OCR without GUI
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Monkey-patch torch.load for YOLO compatibility
import torch
_original_torch_load = torch.load
def patched_torch_load(f, *args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(f, *args, **kwargs)
torch.load = patched_torch_load

from ultralytics import YOLO
import cv2
import easyocr
import numpy as np

print("=" * 70)
print("🚗 PARKING MANAGEMENT SYSTEM - HEADLESS TEST MODE")
print("=" * 70)
print()

# Initialize paths
models_path = Path(__file__).parent / "Automatic-License-Plate-Recognition-using-YOLOv8"
image_dir = Path(__file__).parent / "captured_images"
image_dir.mkdir(exist_ok=True)

# Load YOLO model
print("Loading YOLO license plate detector...", end=" ")
try:
    license_plate_detector = YOLO(str(models_path / 'license_plate_detector.pt'))
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Load EasyOCR
print("Loading EasyOCR reader...", end=" ")
try:
    ocr_reader = easyocr.Reader(['en'], gpu=False)
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test with camera
print("Opening camera...", end=" ")
try:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("✗ Camera not accessible")
        print()
        print("Options:")
        print("  1. Check: ls -la /dev/video*")
        print("  2. Grant access: sudo usermod -a -G video $USER")
        print("  3. Restart system after adding to video group")
        sys.exit(1)
    print("✓")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Configure camera
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)

print()
print("=" * 70)
print("HEADLESS TEST RUNNING")
print("=" * 70)
print()
print("Instructions:")
print("  • Position vehicle in front of camera")
print("  • Press SPACE to capture and process frame")
print("  • Press 'q' to quit")
print()

captured_count = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Display frame info
        h, w = frame.shape[:2]
        print(f"\rFrame: {w}x{h} | Captured: {captured_count}  ", end="", flush=True)
        
        # Wait for key
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):  # Space - capture and process
            print()
            print()
            print(f"⏱️  Processing frame at {datetime.now().strftime('%H:%M:%S')}...")
            
            # Save original frame
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_file = image_dir / f"original_{timestamp}.png"
            cv2.imwrite(str(original_file), frame)
            print(f"✓ Original saved: {original_file.name}")
            
            # Run YOLO detection
            print("  🔍 Running YOLO detection...", end=" ")
            try:
                detections = license_plate_detector(frame)[0]
                detection_count = len(detections.boxes.data)
                print(f"✓ Found {detection_count} plate(s)")
                
                if detection_count > 0:
                    frame_with_boxes = frame.copy()
                    
                    for i, detection in enumerate(detections.boxes.data.tolist(), 1):
                        x1, y1, x2, y2, score, class_id = detection
                        
                        print(f"    Detection {i}: confidence={score:.2f}")
                        
                        # Draw box
                        cv2.rectangle(frame_with_boxes, (int(x1), int(y1)), (int(x2), int(y2)),
                                    (0, 255, 0), 2)
                        
                        # Crop region
                        lp_crop = frame[int(y1):int(y2), int(x1):int(x2), :]
                        
                        if lp_crop.size > 0:
                            # Convert to grayscale
                            lp_gray = cv2.cvtColor(lp_crop, cv2.COLOR_BGR2GRAY)
                            _, lp_thresh = cv2.threshold(lp_gray, 64, 255, cv2.THRESH_BINARY_INV)
                            
                            # Run OCR
                            print(f"      📖 Running OCR...", end=" ")
                            results = ocr_reader.readtext(lp_thresh)
                            
                            if results:
                                plate_text = ''.join([text for (bbox, text, conf) in results])
                                plate_text = plate_text.replace(' ', '').upper()
                                print(f"✓ Read: {plate_text}")
                                
                                # Draw text
                                cv2.putText(frame_with_boxes, f"LP: {plate_text}",
                                          (int(x1), int(y1) - 10),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                          (0, 255, 0), 2)
                            else:
                                print("✓ No text detected")
                    
                    # Save frame with boxes
                    output_file = image_dir / f"detected_{timestamp}.png"
                    cv2.imwrite(str(output_file), frame_with_boxes)
                    print(f"✓ Detection saved: {output_file.name}")
                    
                    captured_count += 1
                else:
                    print("ℹ️  No license plates detected in frame")
                    
            except Exception as e:
                print(f"✗ Error: {e}")
            
            print()
        
        elif key == ord('q'):
            break
        
        elif key == ord('?'):
            print()
            print("Commands:")
            print("  SPACE - Capture and process frame")
            print("  q     - Quit")
            print("  ?     - Show this help")
            print()

except KeyboardInterrupt:
    print()
    print()
    print("Interrupted by user")

finally:
    cap.release()
    print()
    print("=" * 70)
    print(f"✓ Test completed. Processed {captured_count} frame(s)")
    print("=" * 70)
