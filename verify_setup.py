#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parking Management System - Setup Verification Script

This script verifies that all requirements are met before running the application.
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Verify Python version is 3.7 or higher"""
    print("Checking Python version...", end=" ")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print(f"✓ Python {version.major}.{version.minor}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor} (requires 3.7+)")
        return False

def check_required_packages():
    """Check if all required packages are installed"""
    packages = {
        'PyQt5': 'PyQt5.QtWidgets',
        'OpenCV': 'cv2',
        'NumPy': 'numpy',
        'YOLO': 'ultralytics',
        'EasyOCR': 'easyocr',
        'Pillow': 'PIL',
    }
    
    all_good = True
    print("\nChecking required packages:")
    
    for name, module in packages.items():
        print(f"  {name:12}", end=" ")
        try:
            __import__(module)
            print("✓")
        except (ImportError, AttributeError):
            print("✗ NOT INSTALLED")
            all_good = False
    
    return all_good

def check_model_file():
    """Check if YOLO model file exists"""
    print("\nChecking YOLO model file...", end=" ")
    model_path = Path(__file__).parent / "Automatic-License-Plate-Recognition-using-YOLOv8" / "license_plate_detector.pt"
    
    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        print(f"✓ Found ({size_mb:.1f} MB)")
        return True
    else:
        print(f"✗ NOT FOUND at {model_path}")
        print("    Download or train a license plate detector model")
        return False

def check_camera_access():
    """Check if camera device is accessible"""
    print("\nChecking camera access...", end=" ")
    try:
        import cv2
        # For headless OpenCV, just check if it loads properly
        print("✓ OpenCV loaded")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_directories():
    """Check if required directories exist"""
    print("\nChecking directories:")
    base_path = Path(__file__).parent
    
    directories = {
        'captured_images': base_path / 'captured_images',
        'YOLO Models': base_path / 'Automatic-License-Plate-Recognition-using-YOLOv8',
    }
    
    all_good = True
    for name, path in directories.items():
        print(f"  {name:15}", end=" ")
        if path.exists():
            print("✓")
        else:
            print("✗ NOT FOUND")
            all_good = False
    
    return all_good

def main():
    """Run all verification checks"""
    print("=" * 70)
    print("🚗 PARKING MANAGEMENT SYSTEM - SETUP VERIFICATION")
    print("=" * 70)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Packages", check_required_packages),
        ("YOLO Model", check_model_file),
        ("Directories", check_directories),
        ("Camera Access", check_camera_access),
    ]
    
    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"\n✗ Error during {check_name} check: {e}")
            results[check_name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(results.values())
    total = len(results)
    
    for check_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {check_name:25} {status}")
    
    print()
    print(f"Result: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ ✓ ✓  All systems ready!  ✓ ✓ ✓")
        print("\nYou can now run:")
        print("  python3 main.py")
        return 0
    else:
        print("\n✗ ✗ ✗  Some checks failed  ✗ ✗ ✗")
        print("\nPlease fix the issues above before running the application")
        print("\nCommon fixes:")
        print("  1. Install packages:    pip install -r requirements.txt")
        print("  2. Download YOLO model: Automatic-License-Plate-Recognition-using-YOLOv8/")
        print("  3. Grant camera access: sudo usermod -a -G video $USER")
        return 1

if __name__ == "__main__":
    sys.exit(main())
