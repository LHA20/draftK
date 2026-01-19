#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kiểm tra camera và các thiết bị video
"""

import cv2
import os
import subprocess

print("=" * 60)
print("🔍 KIỂM TRA CAMERA VÀ THIẾT BỊ VIDEO")
print("=" * 60)
print()

# Kiểm tra thiết bị video
print("1️⃣  Kiểm tra thiết bị /dev/video*:")
print("-" * 60)
try:
    result = subprocess.run(['ls', '-la', '/dev/video*'], 
                          shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    else:
        print("❌ Không tìm thấy /dev/video*")
except Exception as e:
    print(f"❌ Lỗi: {e}")

print()

# Kiểm tra quyền truy cập
print("2️⃣  Kiểm tra quyền truy cập camera:")
print("-" * 60)
current_user = os.getlogin()
print(f"User hiện tại: {current_user}")

try:
    result = subprocess.run(['groups', current_user], 
                          capture_output=True, text=True)
    print(f"Groups: {result.stdout.strip()}")
    
    if 'video' in result.stdout:
        print("✓ User nằm trong group 'video'")
    else:
        print("⚠️  User KHÔNG nằm trong group 'video'")
        print("   Cách khắc phục:")
        print("   sudo usermod -a -G video $USER")
        print("   newgrp video")
except Exception as e:
    print(f"❌ Lỗi: {e}")

print()

# Kiểm tra OpenCV
print("3️⃣  Kiểm tra OpenCV:")
print("-" * 60)
print(f"OpenCV version: {cv2.__version__}")

# Thử mở camera
print()
print("4️⃣  Thử mở camera:")
print("-" * 60)

for camera_index in range(5):
    cap = cv2.VideoCapture(camera_index)
    if cap.isOpened():
        print(f"✓ Camera {camera_index} - OK")
        
        # Lấy một frame
        ret, frame = cap.read()
        if ret:
            print(f"  - Frame size: {frame.shape}")
        cap.release()
    else:
        print(f"✗ Camera {camera_index} - NOT AVAILABLE")

print()

# Kiểm tra v4l2
print("5️⃣  Kiểm tra V4L2 (Video4Linux2):")
print("-" * 60)
try:
    result = subprocess.run(['which', 'v4l2-ctl'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ v4l2-ctl được cài đặt")
        
        # Liệt kê các thiết bị
        result2 = subprocess.run(['v4l2-ctl', '--list-devices'], 
                               capture_output=True, text=True)
        print("\nDanh sách thiết bị:")
        print(result2.stdout)
    else:
        print("⚠️  v4l2-ctl KHÔNG được cài đặt")
        print("   Cách cài đặt:")
        print("   sudo apt-get install v4l-utils")
except Exception as e:
    print(f"❌ Lỗi: {e}")

print()
print("=" * 60)
print("✓ Kiểm tra hoàn thành")
print("=" * 60)
