#!/bin/bash

# Script chạy ứng dụng Webcam Manager

echo "======================================"
echo "🎥 Webcam Manager - Đang Khởi Động"
echo "======================================"
echo ""

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 không được tìm thấy."
    exit 1
fi

# Chạy ứng dụng
cd "$(dirname "$0")"
python3 main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Lỗi khi chạy ứng dụng!"
    echo ""
    echo "Gợi ý: Kiểm tra các dependencies:"
    echo "  pip install -r requirements.txt"
    exit 1
fi
