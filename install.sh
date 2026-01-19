#!/bin/bash

# Parking Management System - Dependency Installation Script
# This script installs all required Python packages

echo "======================================"
echo "🚗 Parking Management System Setup"
echo "======================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.7 or higher."
    exit 1
fi

echo "✓ Python3 found"
python3 --version
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

echo ""
echo "Installing required packages..."
echo "This may take several minutes (especially YOLO and EasyOCR models)..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "✓ Installation completed successfully!"
    echo "======================================"
    echo ""
    echo "Next steps:"
    echo "  1. Ensure license_plate_detector.pt is in:"
    echo "     ./Automatic-License-Plate-Recognition-using-YOLOv8/"
    echo "  2. Run the application:"
    echo "     python3 main.py"
    echo ""
else
    echo ""
    echo "======================================"
    echo "❌ Installation failed!"
    echo "======================================"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check Python version: python3 --version"
    echo "  - Try manual installation: pip install PyQt5 opencv-python-headless"
    echo "  - Check internet connection"
    echo ""
    exit 1
fi

