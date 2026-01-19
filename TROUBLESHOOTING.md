# 🔧 Hướng Dẫn Cài Đặt Chi Tiết

## Vấn đề: Qt Platform Plugin Error

### Lỗi:
```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
This application failed to start because no Qt platform plugin could be initialized.
```

### Nguyên Nhân:
- `opencv-python` (version thường) bao gồm Qt built-in
- Điều này conflict với PyQt5 khi cả hai cố gắng load cùng một plugin

### Giải Pháp:

**Bước 1: Gỡ cài đặt opencv-python**
```bash
source venv/bin/activate
pip uninstall -y opencv-python
```

**Bước 2: Cài đặt opencv-python-headless**
```bash
pip install opencv-python-headless==4.8.1.78
```

**Bước 3: Kiểm tra**
```bash
pip list | grep opencv
# Output: opencv-python-headless    4.8.1.78
```

**Bước 4: Chạy lại**
```bash
python3 main.py
```

---

## Vấn đề: Camera Không Được Nhận Diện

### Kiểm tra Camera:

**Linux:**
```bash
# Xem danh sách video devices
ls -l /dev/video*

# Kiểm tra quyền
groups $USER
# Nếu không có video group, thêm:
sudo usermod -a -G video $USER
```

**Chạy lại sau khi thêm group:**
```bash
newgrp video
python3 main.py
```

---

## Vấn đề: DeprecationWarning

### Lỗi:
```
DeprecationWarning: sipPyTypeDict() is deprecated
```

### Giải Thích:
- Đây là warning từ PyQt5, không phải lỗi
- Ứng dụng vẫn chạy bình thường
- Có thể bỏ qua an toàn

---

## Vấn đề: Threads Warning

### Lỗi:
```
QObject::moveToThread: Current thread is not the object's thread
```

### Giải Pháp:
Phiên bản hiện tại đã sử dụng `threading.Thread` thay vì `QThread` để tránh vấn đề này.

Nếu bạn vẫn gặp lỗi này:
1. Gỡ cài đặt toàn bộ PyQt5
2. Cài lại: `pip install --upgrade PyQt5`

---

## Kiểm Tra Môi Trường

```bash
source venv/bin/activate

# Kiểm tra Python
python3 --version

# Kiểm tra các thư viện
python3 -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python3 -c "import PyQt5; print('PyQt5: OK')"
python3 -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python3 -c "import PIL; print('Pillow: OK')"
```

---

## Cài Đặt Lại Từ Đầu (Nuclear Option)

Nếu tất cả các cách trên không hoạt động:

```bash
# Xóa venv cũ
rm -rf venv

# Tạo venv mới
python3 -m venv venv

# Kích hoạt
source venv/bin/activate

# Cài đặt dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Nếu gặp lỗi Qt, gỡ opencv-python
pip uninstall -y opencv-python
pip install opencv-python-headless==4.8.1.78

# Chạy
python3 main.py
```

---

## Contact & Hỗ Trợ

Nếu bạn gặp vấn đề khác, hãy:

1. Kiểm tra version Python (phải ≥ 3.7)
2. Đảm bảo webcam hoạt động bình thường
3. Kiểm tra quyền truy cập device `/dev/video0`
4. Cài lại dependencies từ `requirements.txt`

---

**Phiên bản tài liệu**: 1.0  
**Ngày cập nhật**: January 11, 2026
