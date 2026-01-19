#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parking Management System with License Plate Recognition
Integrates YOLO-based license plate detection with OCR
"""

import sys
import os

# Set OpenCV to use a non-GUI backend to avoid Qt conflicts
os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'

from datetime import datetime
from pathlib import Path
import threading
import time
import csv
import string

# Import PyQt5 classes FIRST to initialize Qt platform correctly
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject, QSize

import cv2
import numpy as np
import torch
import easyocr

# Monkey-patch torch.load to allow loading YOLO models without weights_only restriction
_original_torch_load = torch.load

def patched_torch_load(f, *args, **kwargs):
    """Patched torch.load that disables weights_only for YOLO compatibility"""
    kwargs['weights_only'] = False
    return _original_torch_load(f, *args, **kwargs)

torch.load = patched_torch_load

from ultralytics import YOLO

# Initialize OCR reader
OCR_READER = easyocr.Reader(['en'], gpu=False)

# Character mapping for license plate formatting
CHAR_TO_INT_MAP = {'O': '0', 'I': '1', 'J': '3', 'A': '4', 'G': '6', 'S': '5'}
INT_TO_CHAR_MAP = {'0': 'O', '1': 'I', '3': 'J', '4': 'A', '6': 'G', '5': 'S'}


def check_license_format(text):
    """
    Validate if the text complies with standard license plate format.
    Standard format: 2 letters + 4 numbers + 1 letter (e.g., AB1234C)
    
    Args:
        text (str): License plate text to validate
        
    Returns:
        bool: True if format is valid, False otherwise
    """
    # Relaxed validation: Allow 5-10 alphanumeric characters
    if len(text) < 5 or len(text) > 10:
        return False
    
    return text.isalnum()


def format_license_plate(text):
    """
    Convert detected characters to standard license plate format.
    Uses mapping to correct common OCR errors (O->0, I->1, etc.)
    
    Args:
        text (str): Raw OCR-detected text
        
    Returns:
        str: Formatted license plate text
    """
    # Only apply strict mapping if it matches the 7-char pattern length
    if len(text) != 7:
        return text

    formatted = ''
    mapping = {
        0: INT_TO_CHAR_MAP, 1: INT_TO_CHAR_MAP,
        2: CHAR_TO_INT_MAP, 3: CHAR_TO_INT_MAP,
        4: INT_TO_CHAR_MAP, 5: INT_TO_CHAR_MAP, 6: INT_TO_CHAR_MAP
    }
    
    for i in range(7):
        if text[i] in mapping[i]:
            formatted += mapping[i][text[i]]
        else:
            formatted += text[i]
    
    return formatted


def extract_license_plate(license_plate_crop):
    """
    Extract and recognize license plate text from cropped image using OCR.
    Handles both single-line and two-line license plates.
    
    Args:
        license_plate_crop (numpy.ndarray): Cropped image containing the license plate
        
    Returns:
        tuple: (license_plate_text, confidence_score) or (None, None) if invalid
    """
    try:
        print(f"\n📖 Starting OCR processing on crop of size: {license_plate_crop.shape}")
        
        # Preprocess image for better OCR
        if len(license_plate_crop.shape) == 3:
            gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = license_plate_crop.copy()
        
        # Resize if too small
        height, width = gray.shape
        if width < 100:
            scale = 150 / width
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            print(f"   📏 Resized image: {gray.shape}")
        
        # Apply contrast enhancement (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Thresholding for better OCR - try multiple approaches
        _, thresh1 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, thresh2 = cv2.threshold(enhanced, 100, 255, cv2.THRESH_BINARY)
        
        # Try both threshold versions and pick the one with more detections
        detections1 = OCR_READER.readtext(thresh1, detail=1)
        
        if len(detections1) == 0:
            detections = OCR_READER.readtext(thresh2, detail=1)
        else:
            detections = detections1
        
        print(f"   🔍 OCR found {len(detections)} text region(s)")
        
        if not detections:
            print(f"   ❌ No text detected by OCR")
            return None, None
            
        # Sort detections by left-to-right position
        detections.sort(key=lambda x: x[0][0][0])
        
        full_text = ""
        scores = []
        
        for idx, detection in enumerate(detections):
            bbox, text, score = detection
            # Clean text: uppercase, remove spaces, dots, hyphens
            clean_text = text.upper().strip()
            clean_text = ''.join(c for c in clean_text if c.isalnum())
            
            if clean_text:
                full_text += clean_text
                scores.append(score)
                print(f"   ✓ Region {idx+1}: '{text}' → '{clean_text}' (confidence: {score:.3f})")
        
        if not full_text:
            print(f"   ❌ No valid text after processing")
            return None, None
        
        print(f"   📝 Combined text: {full_text}")
            
        # Calculate average confidence
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Always return the detected text (relaxed validation)
        formatted_text = format_license_plate(full_text)
        print(f"✅ OCR Result: {formatted_text} (Score: {avg_score:.2f})")
        return formatted_text, avg_score
            
    except Exception as e:
        print(f"Error during OCR: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    except Exception as e:
        print(f"Error during OCR: {e}")
        return None, None



class CameraSignals(QObject):
    """Signals object to emit events from worker thread"""
    frame_ready = pyqtSignal(np.ndarray)
    error_signal = pyqtSignal(str)
    license_detected = pyqtSignal(str, float)  # license_text, confidence


class CameraWorker(threading.Thread):
    """
    Worker thread for continuous camera capture and YOLO license plate detection.
    Processes frames and detects license plates without blocking UI.
    """
    
    def __init__(self, signals, models_path):
        super().__init__(daemon=True)
        self.signals = signals
        self.is_running = False
        self.cap = None
        
        # Load YOLO models
        try:
            # Allow torch to load YOLO model safely (PyTorch 2.6+ security feature)
            import torch.serialization
            torch.serialization.add_safe_globals([
                torch.nn.modules.container.Sequential,
                torch.nn.modules.conv.Conv2d,
                torch.nn.modules.batchnorm.BatchNorm2d,
                torch.nn.modules.activation.ReLU,
                torch.nn.modules.pooling.MaxPool2d,
                torch.nn.modules.pooling.AdaptiveAvgPool2d,
                torch.nn.modules.linear.Linear,
            ])
            
            self.license_plate_detector = YOLO(str(models_path / 'license_plate_detector.pt'))
            print("✓ License plate detector model loaded successfully")
        except Exception as e:
            self.signals.error_signal.emit(f"Error loading YOLO model: {e}")
            self.license_plate_detector = None
    
    def run(self):
        """Main thread execution: capture frames without processing"""
        try:
            self.is_running = True
            self.cap = cv2.VideoCapture(0)
            
            if not self.cap.isOpened():
                self.signals.error_signal.emit("Cannot open camera. Check /dev/video* and permissions.")
                return
            
            # Configure camera
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            print("✓ Camera initialized successfully")
            
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                # Flip frame horizontally (mirror effect)
                frame = cv2.flip(frame, 1)
                
                # Emit raw frame without YOLO processing
                self.signals.frame_ready.emit(frame)
        
        except Exception as e:
            self.signals.error_signal.emit(f"Camera error: {str(e)}")
        finally:
            if self.cap:
                self.cap.release()
    
    def stop(self):
        """Stop camera capture and release resources"""
        self.is_running = False
        if self.cap:
            self.cap.release()





class ParkingManagementSystem(QMainWindow):
    """
    Parking Management System with License Plate Recognition
    Displays real-time video with YOLO detection and maintains a table of detected plates.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚗 Parking Management System - License Plate Recognition")
        self.setGeometry(50, 50, 1600, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
        """)
        
        # Get path to YOLO models
        self.models_path = Path(__file__).parent / "Automatic-License-Plate-Recognition-using-YOLOv8"
        
        # Data storage
        self.current_frame = None
        self.captured_frame = None
        self.capture_datetime = None
        self.license_records = []  # List of detected license plates
        self.detection_history = {}  # To avoid duplicate detections
        
        # Directory for saving captured images
        self.image_dir = Path(__file__).parent / "captured_images"
        self.image_dir.mkdir(exist_ok=True)
        
        # CSV file for records
        self.csv_file = Path(__file__).parent / "license_plate_records.csv"
        self._init_csv_file()
        
        # Signals
        self.signals = CameraSignals()
        self.signals.frame_ready.connect(self.on_frame_received)
        self.signals.error_signal.connect(self.on_camera_error)
        self.signals.license_detected.connect(self.on_license_detected)
        
        # Initialize UI
        self.init_ui()
        
        # Camera thread (not started yet)
        self.camera_thread = None
        
        # Use timer to start camera after UI is shown
        self.start_timer = QTimer()
        self.start_timer.setSingleShot(True)
        self.start_timer.timeout.connect(self.start_camera)
        
    def start_camera(self):
        """Start camera thread after UI is shown"""
        if self.camera_thread is None:
            self.camera_thread = CameraWorker(self.signals, self.models_path)
            self.camera_thread.start()
            print("✓ Camera thread started")
    
    def _init_csv_file(self):
        """Initialize CSV file for storing license plate records"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['License Plate', 'Detection Time', 'Confidence'])
    
    def init_ui(self):
        """Initialize user interface with camera feed and records table"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - split into left (video) and right (controls + table)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # ===== LEFT PANEL: Live Camera Feed with YOLO Detection =====
        left_layout = QVBoxLayout()
        
        # Header
        left_header = QLabel("🎥 LIVE CAMERA FEED WITH LICENSE PLATE DETECTION")
        left_header.setFont(self._create_header_font())
        left_header.setAlignment(Qt.AlignCenter)
        left_header.setStyleSheet("""
            background-color: #2c3e50;
            color: white;
            padding: 12px;
            border-radius: 5px;
        """)
        left_layout.addWidget(left_header)
        
        # Camera display
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("""
            border: 3px solid #34495e;
            background-color: #000000;
            border-radius: 5px;
        """)
        self.camera_label.setMinimumSize(800, 600)
        left_layout.addWidget(self.camera_label)
        
        # ===== RIGHT PANEL: Controls and License Plate Table =====
        right_layout = QVBoxLayout()
        
        # Capture section header
        capture_header = QLabel("CAPTURE & MANAGEMENT")
        capture_header.setFont(self._create_header_font())
        capture_header.setAlignment(Qt.AlignCenter)
        capture_header.setStyleSheet("""
            background-color: #27ae60;
            color: white;
            padding: 12px;
            border-radius: 5px;
        """)
        right_layout.addWidget(capture_header)
        
        # Capture button
        self.capture_button = QPushButton("CAPTURE IMAGE")
        self.capture_button.setFont(self._create_button_font())
        self.capture_button.setMinimumHeight(50)
        self.capture_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.capture_button.clicked.connect(self.capture_image)
        right_layout.addWidget(self.capture_button)
        
        # Last captured image preview
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("⏳ No image captured yet")
        self.preview_label.setStyleSheet("""
            border: 2px solid #bdc3c7;
            background-color: #ecf0f1;
            border-radius: 5px;
            color: #7f8c8d;
        """)
        self.preview_label.setMinimumSize(280, 200)
        right_layout.addWidget(self.preview_label)
        
        # License plate table header
        table_header = QLabel("📋 DETECTED LICENSE PLATES")
        table_header.setFont(self._create_header_font())
        table_header.setAlignment(Qt.AlignCenter)
        table_header.setStyleSheet("""
            background-color: #3498db;
            color: white;
            padding: 10px;
            border-radius: 5px;
        """)
        right_layout.addWidget(table_header)
        
        # License plate records table
        self.license_table = QTableWidget()
        self.license_table.setColumnCount(2)
        self.license_table.setHorizontalHeaderLabels(['License Plate', 'Detection Time'])
        self.license_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.license_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.license_table.setMaximumHeight(250)
        self.license_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #bdc3c7;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 5px;
                border: none;
            }
        """)
        right_layout.addWidget(self.license_table)
        
        # Status label
        self.status_label = QLabel("Status: Initializing...")
        self.status_label.setFont(QFont("Arial", 9))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #7f8c8d;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 5px;
        """)
        right_layout.addWidget(self.status_label)
        
        right_layout.addStretch()
        
        # Add panels to main layout
        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 1)
    
    def _create_header_font(self):
        """Create font for section headers"""
        font = QFont("Arial", 11)
        font.setBold(True)
        return font
    
    def _create_button_font(self):
        """Create font for buttons"""
        font = QFont("Arial", 10)
        font.setBold(True)
        return font
    
    def on_frame_received(self, frame):
        """Handle new frame from camera worker"""
        self.current_frame = frame
        self.display_camera_frame(frame)
    
    def on_camera_error(self, error_msg):
        """Handle camera errors"""
        print(f"Camera Error: {error_msg}")
        self.camera_label.setText(f"❌ {error_msg}")
        self.status_label.setText(f"Status: Error - {error_msg}")
    
    def on_license_detected(self, license_text, confidence):
        """Handle detection of a new license plate"""
        current_time = datetime.now()
        time_key = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Print to terminal
        print(f"\n{'*'*70}")
        print(f"🚗 LICENSE PLATE DETECTED")
        print(f"{'*'*70}")
        print(f"  📋 Plate Number: {license_text}")
        print(f"  ⏰ Time: {time_key}")
        print(f"  📊 Confidence: {confidence:.2%}")
        print(f"{'*'*70}\n")
        
        # Avoid duplicate detections within same second
        if license_text not in self.detection_history or \
           (current_time - self.detection_history[license_text]).total_seconds() > 2:
            
            self.detection_history[license_text] = current_time
            
            # Add to records list
            self.license_records.append({
                'license': license_text,
                'time': time_key,
                'confidence': f"{confidence:.2%}"
            })
            
            print(f"✓ Added to table and CSV")
            
            # Update table
            self.update_license_table()
            
            # Save to CSV
            self.save_to_csv(license_text, time_key, confidence)
            
            # Update status
            self.status_label.setText(f"Status: Detected - {license_text}")
    
    def display_camera_frame(self, frame):
        """Display frame with YOLO detection boxes"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to QImage
            h, w, ch = rgb_frame.shape
            bytes_per_line = 3 * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Display with scaling
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaledToWidth(750, Qt.SmoothTransformation)
            self.camera_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error displaying frame: {e}")
    
    def capture_image(self):
        """Capture current frame, detect license plates with YOLO+OCR, and save with metadata"""
        if self.current_frame is None:
            self.status_label.setText("Status: Error - No frame to capture")
            return
        
        try:
            now = datetime.now()
            self.capture_datetime = now
            
            # Create filename with timestamp
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp_str}.png"
            filepath = self.image_dir / filename
            
            # Clone frame for YOLO processing
            frame_with_boxes = self.current_frame.copy()
            detected_plates = []
            
            print(f"\n{'='*70}")
            print(f"📸 CAPTURING IMAGE AT {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}")
            
            # Process with YOLO license plate detection
            if self.camera_thread and self.camera_thread.license_plate_detector:
                try:
                    print(f"\n🔍 Running YOLO detection...")
                    
                    # Detect license plates
                    detections = self.camera_thread.license_plate_detector(self.current_frame)[0]
                    
                    plate_count = len(detections.boxes.data)
                    print(f"   Found {plate_count} plate candidate(s)")
                    
                    # Process each detection
                    for det_idx, detection in enumerate(detections.boxes.data.tolist()):
                        x1, y1, x2, y2, score, class_id = detection
                        
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        
                        print(f"\n   📍 Detection {det_idx + 1}/{plate_count}")
                        print(f"      Box coordinates: ({x1}, {y1}) to ({x2}, {y2})")
                        print(f"      YOLO confidence: {score:.3f}")
                        
                        # Draw bounding box on frame
                        cv2.rectangle(frame_with_boxes, (x1, y1), (x2, y2), 
                                    (0, 255, 0), 3)
                        
                        # Crop license plate for OCR
                        lp_crop = self.current_frame[y1:y2, x1:x2, :].copy()
                        
                        if lp_crop.size > 0:
                            crop_h, crop_w = lp_crop.shape[:2]
                            print(f"      Crop size: {crop_w}×{crop_h}")
                            
                            # Extract license plate text using OCR
                            lp_text, lp_score = extract_license_plate(lp_crop)
                            
                            if lp_text:
                                print(f"\n      ✅ LICENSE PLATE DETECTED: {lp_text}")
                                print(f"      OCR Confidence: {lp_score:.3f}")
                                
                                detected_plates.append({
                                    'text': lp_text,
                                    'confidence': float(lp_score) if lp_score else 0.0,
                                    'time': now.strftime("%H:%M:%S")
                                })
                                
                                # Display license plate text on frame (bigger and clearer)
                                cv2.putText(frame_with_boxes, f"LP: {lp_text}", 
                                          (x1, y1 - 20),
                                          cv2.FONT_HERSHEY_SIMPLEX, 1.2, 
                                          (0, 255, 0), 3)
                                
                                # Draw confidence score
                                conf_text = f"Confidence: {lp_score:.2%}"
                                cv2.putText(frame_with_boxes, conf_text,
                                          (x1, y2 + 40),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                                          (0, 255, 0), 2)
                            else:
                                print(f"      ❌ Failed to extract license plate from this region")
                        else:
                            print(f"      ❌ Invalid crop region")
                    
                    print(f"\n   📊 Total plates detected: {len(detected_plates)}")
                
                except Exception as e:
                    print(f"❌ Error during YOLO detection: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Save image with bounding boxes
            cv2.imwrite(str(filepath), frame_with_boxes)
            print(f"\n✓ Image saved: {filepath}")
            
            # Display preview with detection boxes
            rgb_frame = cv2.cvtColor(frame_with_boxes, cv2.COLOR_BGR2RGB)
            small_frame = cv2.resize(rgb_frame, (280, 200))
            
            h, w, ch = small_frame.shape
            bytes_per_line = 3 * w
            qt_image = QImage(small_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            pixmap = QPixmap.fromImage(qt_image)
            self.preview_label.setPixmap(pixmap)
            
            # Update table with detected plates
            if detected_plates:
                for plate_info in detected_plates:
                    self.on_license_detected(plate_info['text'], plate_info['confidence'])
                
                plate_list = ", ".join([p['text'] for p in detected_plates])
                status_msg = f"Status: Captured - Detected: {plate_list}"
                print(f"\n{'='*70}")
                print(f"✅ {status_msg}")
                print(f"{'='*70}\n")
            else:
                status_msg = "Status: Captured - No license plates detected"
                print(f"\n{'='*70}")
                print(f"⚠️  {status_msg}")
                print(f"{'='*70}\n")
            
            self.status_label.setText(status_msg)
        
        except Exception as e:
            error_msg = f"Error capturing image: {str(e)}"
            print(f"\n❌ {error_msg}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Status: {error_msg}")
    
    def update_license_table(self):
        """Update the license plate table with latest records"""
        self.license_table.setRowCount(len(self.license_records))
        
        # Display in reverse order (newest first)
        for row, record in enumerate(reversed(self.license_records)):
            # License plate cell (column 0)
            plate_item = QTableWidgetItem(record['license'])
            plate_item.setBackground(QColor(200, 255, 200))  # Light green
            self.license_table.setItem(row, 0, plate_item)
            
            # Time cell (column 1)
            time_item = QTableWidgetItem(record['time'])
            time_item.setBackground(QColor(240, 248, 255))  # Light blue
            self.license_table.setItem(row, 1, time_item)
            
            # Confidence cell (column 2)
            conf_item = QTableWidgetItem(str(record['confidence']))
            conf_item.setBackground(QColor(255, 255, 200))  # Light yellow
            self.license_table.setItem(row, 2, conf_item)
        
        # Scroll to bottom to show latest
        self.license_table.scrollToBottom()
    
    def save_to_csv(self, license_plate, timestamp, confidence):
        """Save detected license plate record to CSV file"""
        try:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([license_plate, timestamp, f"{confidence:.2f}"])
        except Exception as e:
            print(f"Error saving to CSV: {e}")
    
    def closeEvent(self, event):
        """Handle application close event"""
        print("\n🛑 Closing application...")
        self.camera_thread.stop()
        event.accept()


def main():
    """Main function to launch the Parking Management System"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    print("=" * 70)
    print("Parking Management System")
    print("=" * 70)
    print()
    
    try:
        window = ParkingManagementSystem()
        window.show()
        
        print(f"✓ Window displayed")
        
        # Start camera thread after window is shown (delay slightly to ensure UI is ready)
        window.start_timer.start(500)  # 500ms delay
        
        print(f"✓ Application ready")
        print()
        
        sys.exit(app.exec_())
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
