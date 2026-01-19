#!/usr/bin/env python3
"""
Test OCR separately without GUI
"""

import sys
from pathlib import Path

# Monkey-patch torch first
import torch
_orig = torch.load
def patched_load(f, *args, **kwargs):
    kwargs['weights_only'] = False
    return _orig(f, *args, **kwargs)
torch.load = patched_load

import cv2
import numpy as np
import easyocr

print("=" * 70)
print("🧪 OCR TEST - License Plate Recognition")
print("=" * 70)
print()

# Initialize OCR
print("Loading OCR reader...", end=" ")
try:
    ocr = easyocr.Reader(['en'], gpu=False)
    print("✓")
except Exception as e:
    print(f"✗ {e}")
    sys.exit(1)

# Test with a sample image
print("Opening camera...", end=" ")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("✗ Cannot open camera")
    sys.exit(1)
print("✓")

print()
print("Instructions:")
print("  1. Position license plate in front of camera")
print("  2. Press SPACE to capture and test OCR")
print("  3. Press 'q' to quit")
print()

frame_count = 0
test_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    if frame_count % 30 == 0:
        print(f"\rFrames: {frame_count} | Tests: {test_count}  ", end="", flush=True)
    
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord(' '):
        print()
        print()
        print("=" * 70)
        print(f"📸 TEST #{test_count + 1}")
        print("=" * 70)
        
        test_count += 1
        
        # Detect license plates
        h, w = frame.shape[:2]
        small_frame = cv2.resize(frame, (384, 640))
        
        print("  🔍 Simulating YOLO detection (manual region)...")
        print(f"  Frame size: {w}x{h}")
        
        # Manually define a region (typically where license plate is)
        # This simulates a YOLO detection crop
        y1, y2 = int(h * 0.2), int(h * 0.6)
        x1, x2 = int(w * 0.2), int(w * 0.8)
        
        crop = frame[y1:y2, x1:x2, :].copy()
        print(f"  📍 Crop region: ({x1}, {y1}) to ({x2}, {y2}), size: {crop.shape}")
        
        # Preprocess
        if len(crop.shape) == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop
        
        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # Threshold
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        print(f"  🔄 Preprocessed image: {thresh.shape}")
        
        # OCR
        print("  📖 Running EasyOCR...", end=" ")
        try:
            detections = ocr.readtext(thresh, detail=1)
            print(f"✓ Found {len(detections)} region(s)")
            
            if detections:
                full_text = ""
                scores = []
                
                for idx, (bbox, text, score) in enumerate(detections):
                    clean = text.upper().strip()
                    clean = ''.join(c for c in clean if c.isalnum())
                    
                    if clean:
                        full_text += clean
                        scores.append(score)
                        print(f"     Region {idx+1}: '{text}' → '{clean}' (score: {score:.3f})")
                
                if full_text:
                    avg_score = sum(scores) / len(scores)
                    print()
                    print(f"  ✅ EXTRACTED PLATE: {full_text}")
                    print(f"     Average Confidence: {avg_score:.2%}")
                else:
                    print(f"  ❌ No valid text found")
            else:
                print(f"  ❌ OCR found no text regions")
        
        except Exception as e:
            print(f"✗ {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    elif key == ord('q'):
        break

cap.release()
print()
print(f"✓ Test completed. Processed {test_count} capture(s)")
