#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parking Management System - Complete Version with Serial Port Support
Integrated YOLO license plate detection, EasyOCR text extraction, and Arduino/ESP32 RFID reader support
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import threading
import csv
import json
import serial
import serial.tools.list_ports

import cv2
import numpy as np
import torch

# Monkey-patch torch.load to disable security check for YOLO model loading
_original_torch_load = torch.load
def patched_torch_load(f, *args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(f, *args, **kwargs)
torch.load = patched_torch_load

from ultralytics import YOLO
import easyocr

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QLineEdit,
    QMessageBox, QHeaderView, QFileDialog, QComboBox, QGroupBox
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject

# Pre-load OCR reader to avoid delays during first capture
print("Loading OCR reader...", end=" ", flush=True)
OCR_READER = easyocr.Reader(['en'], gpu=False)
print("✓")


class CameraSignals(QObject):
    """Signal emitter for camera worker thread events"""
    frame_ready = pyqtSignal(np.ndarray)  # Emitted when new frame is captured
    error_signal = pyqtSignal(str)  # Emitted when camera error occurs


class SerialSignals(QObject):
    """Signal emitter for serial port worker thread events"""
    data_received = pyqtSignal(dict)  # Emitted when JSON card scan data received
    connection_status = pyqtSignal(bool, str)  # Emitted when connection status changes (connected, message)
    error_signal = pyqtSignal(str)  # Emitted when serial communication error occurs


class CameraWorker(threading.Thread):
    """Worker thread for continuous 30 FPS camera capture and YOLO inference"""
    
    def __init__(self, signals, models_path):
        super().__init__(daemon=True)
        self.signals = signals
        self.is_running = False
        self.cap = None
        self.license_plate_detector = None
        
        # Load YOLO model for license plate detection
        try:
            self.license_plate_detector = YOLO(str(models_path / 'license_plate_detector.pt'))
            print("✓ License plate detector model loaded")
        except Exception as e:
            self.signals.error_signal.emit(f"Error loading YOLO model: {e}")
    
    def run(self):
        """Continuously capture frames from webcam at 30 FPS"""
        try:
            self.is_running = True
            self.cap = cv2.VideoCapture(0)
            
            if not self.cap.isOpened():
                self.signals.error_signal.emit("Cannot open camera")
                return
            
            # Set video capture parameters
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            print("✓ Camera initialized")
            
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                # Mirror the frame for better UX
                frame = cv2.flip(frame, 1)
                self.signals.frame_ready.emit(frame)
        
        except Exception as e:
            self.signals.error_signal.emit(f"Camera error: {str(e)}")
        finally:
            if self.cap:
                self.cap.release()
    
    def stop(self):
        """Stop the camera thread gracefully"""
        self.is_running = False


class SerialWorker(threading.Thread):
    """Worker thread for serial port communication with Arduino/ESP32 RFID reader"""
    
    def __init__(self, signals):
        super().__init__(daemon=True)
        self.signals = signals
        self.is_running = False
        self.serial_port = None
        self.port_name = None
        self.baud_rate = None
    
    def set_connection(self, port_name, baud_rate):
        """Configure port and baud rate before connection"""
        self.port_name = port_name
        self.baud_rate = baud_rate
    
    def run(self):
        """Listen for incoming JSON data from serial port"""
        try:
            if not self.port_name or not self.baud_rate:
                self.signals.error_signal.emit("Port or baud rate not set")
                return
            
            self.serial_port = serial.Serial(
                port=self.port_name,
                baudrate=self.baud_rate,
                timeout=1,
                write_timeout=1
            )
            
            self.is_running = True
            self.signals.connection_status.emit(True, f"Connected to {self.port_name} @ {self.baud_rate}")
            print(f"✓ Serial port connected: {self.port_name} @ {self.baud_rate} baud")
            
            while self.is_running:
                try:
                    if self.serial_port.in_waiting > 0:
                        line = self.serial_port.readline().decode('utf-8').strip()
                        
                        if line:
                            try:
                                # Parse JSON data from Arduino/ESP32
                                data = json.loads(line)
                                # Validate JSON contains required fields
                                if 'event' in data and 'uid' in data:
                                    self.signals.data_received.emit(data)
                                    print(f"Card scanned: {data.get('uid')} - Gate: {data.get('gate')}")
                            except json.JSONDecodeError as e:
                                self.signals.error_signal.emit(f"Invalid JSON: {line}")
                
                except Exception as e:
                    if self.is_running:
                        self.signals.error_signal.emit(f"Serial read error: {str(e)}")
                    break
        
        except serial.SerialException as e:
            self.signals.error_signal.emit(f"Serial connection error: {str(e)}")
            self.signals.connection_status.emit(False, "Disconnected")
        except Exception as e:
            self.signals.error_signal.emit(f"Serial worker error: {str(e)}")
        finally:
            self.is_running = False
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.signals.connection_status.emit(False, "Disconnected")
    
    def stop(self):
        """Stop serial worker and close port gracefully"""
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()


def get_available_ports():
    """Auto-detect available serial ports from connected devices"""
    ports = []
    for port_info in serial.tools.list_ports.comports():
        ports.append((port_info.device, port_info.description))
    return ports



def extract_license_plate(crop):
    """Extract license plate text using OCR with preprocessing"""
    try:
        if crop.size == 0:
            return None, None
        
        # Convert BGR to Grayscale
        if len(crop.shape) == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # Apply binary threshold with Otsu's method
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Run EasyOCR on preprocessed image
        results = OCR_READER.readtext(binary, detail=1)
        
        if not results:
            return None, None
        
        # Combine extracted text and calculate average confidence
        full_text = ""
        total_score = 0.0
        
        for (bbox, text, score) in results:
            clean_text = text.upper().strip().replace(' ', '').replace('.', '')
            clean_text = ''.join(c for c in clean_text if c.isalnum())
            
            if clean_text:
                full_text += clean_text
                total_score += score
        
        # Return only if extracted text has minimum length (license plate)
        if full_text and len(full_text) >= 4:
            avg_score = total_score / len(results) if results else 0.0
            return full_text.upper(), avg_score
        
        return None, None
    
    except Exception as e:
        print(f"OCR Error: {e}")
        return None, None


class ParkingManagementUI(QMainWindow):
    """Main window for Parking Management System with YOLO detection and serial port support"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🅿️ Parking Management System")
        self.setGeometry(50, 50, 1920, 1080)
        
        # Data storage
        self.parking_records = []
        self.models_path = Path(__file__).parent / "Automatic-License-Plate-Recognition-using-YOLOv8"
        self.csv_file = Path(__file__).parent / "parking_records.csv"
        self.current_frame = None
        self.captured_license_plate = None  # Store extracted license plate from OCR
        
        # Temporary variables for serial card processing
        self.pending_card_data = None  # Store card data while waiting for OCR
        self.is_processing_card = False  # Flag to prevent concurrent card processing
        
        # Initialize CSV file
        self._init_csv()
        
        # Camera Signals
        self.signals = CameraSignals()
        self.signals.frame_ready.connect(self.on_frame_received)
        self.signals.error_signal.connect(self.on_camera_error)
        
        # Serial Signals
        self.serial_signals = SerialSignals()
        self.serial_signals.data_received.connect(self.on_card_scanned)
        self.serial_signals.connection_status.connect(self.on_serial_status_changed)
        self.serial_signals.error_signal.connect(self.on_serial_error)
        
        # Serial worker thread
        self.serial_thread = None
        self.serial_connected = False
        
        # Build user interface
        self.init_ui()
        
        # Start camera worker thread
        self.camera_thread = CameraWorker(self.signals, self.models_path)
        self.camera_thread.start()
        
        # Startup timer for initialization message
        self.start_timer = QTimer()
        self.start_timer.setSingleShot(True)
        self.start_timer.timeout.connect(lambda: print("✓ System ready"))
    
    def _init_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Card ID', 'License Plate', 'Time In', 'Time Out', 'Slot Number', 'Status', 'Fee (VND)'])
    
    def init_ui(self):
        """Initialize user interface"""
        central = QWidget()
        central.setStyleSheet("background-color: #f5f6fa;")
        self.setCentralWidget(central)
        
        # ===== MAIN LAYOUT =====
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # ====================== LEFT PANEL (Smaller, Top-Left Video + Bottom Snapshot) ======================
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_panel = QWidget()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(620)
        left_panel.setStyleSheet("background-color: white; border-radius: 10px; border: 2px solid #e0e0e0;")
        
        # ---- VIDEO FEED SECTION (Top Left) ----
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setSpacing(6)
        video_layout.setContentsMargins(12, 12, 12, 12)
        video_container.setStyleSheet("background-color: white;")
        
        # Video header with icon
        video_header = QLabel("📹 LIVE CAMERA FEED")
        video_header.setFont(QFont("Arial", 10, QFont.Bold))
        video_header.setAlignment(Qt.AlignCenter)
        video_header.setStyleSheet(
            "background-color: #1e3a8a; color: white; padding: 8px; border-radius: 5px; "
            "font-weight: bold; letter-spacing: 1px;"
        )
        video_layout.addWidget(video_header)
        
        # Camera label (Compact size - 400x280)
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(480, 320)
        self.camera_label.setMaximumSize(580, 380)
        self.camera_label.setStyleSheet(
            "border: 3px solid #1e3a8a; background-color: #000000; border-radius: 8px; padding: 0px;"
        )
        video_layout.addWidget(self.camera_label, alignment=Qt.AlignCenter)
        video_layout.addStretch()
        
        left_layout.addWidget(video_container)
        
        # ---- SNAPSHOT SECTION (Bottom) ----
        snapshot_container = QWidget()
        snapshot_layout = QVBoxLayout(snapshot_container)
        snapshot_layout.setSpacing(6)
        snapshot_layout.setContentsMargins(12, 12, 12, 12)
        snapshot_container.setStyleSheet("background-color: white;")
        
        # Snapshot header
        snapshot_header = QLabel("📸 CAPTURED LICENSE PLATE IMAGE")
        snapshot_header.setFont(QFont("Arial", 10, QFont.Bold))
        snapshot_header.setAlignment(Qt.AlignCenter)
        snapshot_header.setStyleSheet(
            "background-color: #059669; color: white; padding: 8px; border-radius: 5px; "
            "font-weight: bold; letter-spacing: 1px;"
        )
        snapshot_layout.addWidget(snapshot_header)
        
        # Snapshot display label
        self.snapshot_label = QLabel()
        self.snapshot_label.setAlignment(Qt.AlignCenter)
        self.snapshot_label.setMinimumSize(480, 120)
        self.snapshot_label.setMaximumSize(580, 160)
        self.snapshot_label.setStyleSheet(
            "border: 2px dashed #059669; background-color: #ecfdf5; border-radius: 6px; "
            "color: #047857; font-weight: bold;"
        )
        self.snapshot_label.setText("No snapshot captured yet\nClick 'CAPTURE LICENSE PLATE' to start")
        snapshot_layout.addWidget(self.snapshot_label, alignment=Qt.AlignCenter)
        
        # Extracted license plate label (Large, Bold)
        plate_info_header = QLabel("🔤 EXTRACTED TEXT")
        plate_info_header.setFont(QFont("Arial", 9, QFont.Bold))
        plate_info_header.setAlignment(Qt.AlignCenter)
        plate_info_header.setStyleSheet(
            "background-color: #7c3aed; color: white; padding: 6px; border-radius: 4px; margin-top: 8px;"
        )
        snapshot_layout.addWidget(plate_info_header)
        
        self.extracted_plate_label = QLabel("Awaiting capture...")
        self.extracted_plate_label.setAlignment(Qt.AlignCenter)
        self.extracted_plate_label.setFont(QFont("Courier New", 16, QFont.Bold))
        self.extracted_plate_label.setStyleSheet(
            "background-color: #f3e8ff; color: #6d28d9; padding: 10px; "
            "border-radius: 6px; border: 2px solid #7c3aed; letter-spacing: 2px;"
        )
        snapshot_layout.addWidget(self.extracted_plate_label)
        
        left_layout.addWidget(snapshot_container)
        
        # ---- PARKING SLOTS SECTION (Bottom) ----
        slots_container = QWidget()
        slots_layout = QVBoxLayout(slots_container)
        slots_layout.setSpacing(6)
        slots_layout.setContentsMargins(12, 12, 12, 12)
        slots_container.setStyleSheet("background-color: white;")
        
        # Slots header
        slots_header = QLabel("🅿️ PARKING SLOTS STATUS")
        slots_header.setFont(QFont("Arial", 10, QFont.Bold))
        slots_header.setAlignment(Qt.AlignCenter)
        slots_header.setStyleSheet(
            "background-color: #1f2937; color: white; padding: 8px; border-radius: 5px; "
            "font-weight: bold; letter-spacing: 1px;"
        )
        slots_layout.addWidget(slots_header)
        
        # Grid of parking slots (3 rows x 4 columns = 12 slots)
        slots_grid = QWidget()
        grid_layout = QVBoxLayout(slots_grid)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(8, 8, 8, 8)
        
        # Initialize slot buttons/labels (12 slots)
        self.slot_buttons = []
        
        for row in range(3):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setSpacing(8)
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            for col in range(4):
                slot_num = row * 4 + col + 1  # Slot 1-12
                
                slot_btn = QPushButton(f"SLOT {slot_num}")
                slot_btn.setMinimumHeight(50)
                slot_btn.setFont(QFont("Arial", 9, QFont.Bold))
                slot_btn.setStyleSheet(
                    "QPushButton {"
                    "  background-color: #10b981;"
                    "  color: white;"
                    "  font-weight: bold;"
                    "  border-radius: 6px;"
                    "  border: 2px solid #059669;"
                    "  padding: 6px;"
                    "}"
                    "QPushButton:hover {"
                    "  background-color: #059669;"
                    "}"
                )
                slot_btn.setEnabled(False)  # Disable clicking
                
                self.slot_buttons.append({
                    'button': slot_btn,
                    'slot_num': slot_num,
                    'is_occupied': False
                })
                
                row_layout.addWidget(slot_btn)
            
            grid_layout.addWidget(row_widget)
        
        slots_grid.setStyleSheet("background-color: white;")
        slots_layout.addWidget(slots_grid)
        
        left_layout.addWidget(slots_container)
        left_layout.addStretch()
        
        # ====================== RIGHT PANEL (Professional Controls) ======================
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_panel = QWidget()
        right_panel.setLayout(right_layout)
        right_panel.setStyleSheet("background-color: white; border-radius: 10px; border: 2px solid #e0e0e0;")
        
        # Scroll area for better organization
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(12, 12, 12, 12)
        
        # ============ SECTION 0: SERIAL PORT CONFIGURATION ============
        serial_section = QWidget()
        serial_layout = QVBoxLayout(serial_section)
        serial_layout.setSpacing(8)
        serial_layout.setContentsMargins(10, 10, 10, 10)
        
        serial_header = QLabel("🔌 ARDUINO/ESP32 CONFIGURATION")
        serial_header.setFont(QFont("Arial", 10, QFont.Bold))
        serial_header.setAlignment(Qt.AlignCenter)
        serial_header.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 8px; border-radius: 5px; "
            "font-weight: bold; letter-spacing: 0.5px;"
        )
        serial_layout.addWidget(serial_header)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_label = QLabel("Port")
        port_label.setFont(QFont("Arial", 9, QFont.Bold))
        port_label.setMinimumWidth(120)
        port_label.setStyleSheet("color: #374151;")
        port_layout.addWidget(port_label)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumHeight(32)
        self.port_combo.setStyleSheet(
            "border: 2px solid #d1d5db; border-radius: 5px; padding: 6px; background-color: #f9fafb;"
            "QComboBox:focus { border: 2px solid #2563eb; }"
        )
        self._refresh_ports()
        port_layout.addWidget(self.port_combo)
        
        refresh_port_btn = self._create_button("🔄", "#6b7280", "#4b5563", 32, self._refresh_ports)
        refresh_port_btn.setMaximumWidth(50)
        port_layout.addWidget(refresh_port_btn)
        serial_layout.addLayout(port_layout)
        
        # Baud rate selection
        baud_layout = QHBoxLayout()
        baud_label = QLabel("Baud Rate")
        baud_label.setFont(QFont("Arial", 9, QFont.Bold))
        baud_label.setMinimumWidth(120)
        baud_label.setStyleSheet("color: #374151;")
        baud_layout.addWidget(baud_label)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.baud_combo.setCurrentText('9600')
        self.baud_combo.setMinimumHeight(32)
        self.baud_combo.setStyleSheet(
            "border: 2px solid #d1d5db; border-radius: 5px; padding: 6px; background-color: #f9fafb;"
            "QComboBox:focus { border: 2px solid #2563eb; }"
        )
        baud_layout.addWidget(self.baud_combo)
        serial_layout.addLayout(baud_layout)
        
        # Connection status indicator and button
        status_layout = QHBoxLayout()
        self.serial_status_label = QLabel("🔴 Disconnected")
        self.serial_status_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.serial_status_label.setStyleSheet("color: #dc2626;")
        status_layout.addWidget(self.serial_status_label)
        status_layout.addStretch()
        
        self.serial_connect_btn = self._create_button(
            "🔗 CONNECT",
            "#2563eb",
            "#1d4ed8",
            32,
            self.toggle_serial_connection
        )
        status_layout.addWidget(self.serial_connect_btn)
        serial_layout.addLayout(status_layout)
        
        serial_section.setStyleSheet(
            "background-color: white; border: 1px solid #e5e7eb; border-radius: 6px;"
        )
        scroll_layout.addWidget(serial_section)
        
        # ============ SECTION 1: CHECK IN (Vehicle Entry) ============
        checkin_section = QWidget()
        checkin_layout = QVBoxLayout(checkin_section)
        checkin_layout.setSpacing(8)
        checkin_layout.setContentsMargins(10, 10, 10, 10)
        
        checkin_header = QLabel("🚗 CHECK IN - VEHICLE ENTRY")
        checkin_header.setFont(QFont("Arial", 10, QFont.Bold))
        checkin_header.setAlignment(Qt.AlignCenter)
        checkin_header.setStyleSheet(
            "background-color: #059669; color: white; padding: 8px; border-radius: 5px; "
            "font-weight: bold; letter-spacing: 0.5px;"
        )
        checkin_layout.addWidget(checkin_header)
        
        # Card ID input
        card_layout = QHBoxLayout()
        card_label = QLabel("Card ID")
        card_label.setFont(QFont("Arial", 9, QFont.Bold))
        card_label.setMinimumWidth(120)
        card_label.setStyleSheet("color: #374151;")
        card_layout.addWidget(card_label)
        self.card_id_input = QLineEdit()
        self.card_id_input.setPlaceholderText("Enter card ID...")
        self.card_id_input.setMinimumHeight(32)
        self.card_id_input.setStyleSheet(
            "border: 2px solid #d1d5db; border-radius: 5px; padding: 6px; background-color: #f9fafb;"
            "QLineEdit:focus { border: 2px solid #059669; background-color: white; }"
        )
        card_layout.addWidget(self.card_id_input)
        checkin_layout.addLayout(card_layout)
        
        # Slot Number input
        slot_layout = QHBoxLayout()
        slot_label = QLabel("Parking Slot")
        slot_label.setFont(QFont("Arial", 9, QFont.Bold))
        slot_label.setMinimumWidth(120)
        slot_label.setStyleSheet("color: #374151;")
        slot_layout.addWidget(slot_label)
        self.slot_input = QLineEdit()
        self.slot_input.setPlaceholderText("Enter slot number...")
        self.slot_input.setMinimumHeight(32)
        self.slot_input.setStyleSheet(
            "border: 2px solid #d1d5db; border-radius: 5px; padding: 6px; background-color: #f9fafb;"
            "QLineEdit:focus { border: 2px solid #059669; background-color: white; }"
        )
        slot_layout.addWidget(self.slot_input)
        checkin_layout.addLayout(slot_layout)
        
        checkin_section.setStyleSheet(
            "background-color: white; border: 1px solid #e5e7eb; border-radius: 6px;"
        )
        scroll_layout.addWidget(checkin_section)
        
        # Capture button - More prominent
        self.capture_btn = self._create_button(
            "📸 CAPTURE LICENSE PLATE",
            "#0891b2",
            "#06b6d4",
            45,
            self.capture_plate
        )
        scroll_layout.addWidget(self.capture_btn)
        
        # Check-in button
        self.checkin_btn = self._create_button(
            "✅ CHECK IN (IN)",
            "#059669",
            "#047857",
            42,
            self.check_in
        )
        scroll_layout.addWidget(self.checkin_btn)
        
        # ============ SECTION 2: CHECK OUT (Vehicle Exit) ============
        checkout_section = QWidget()
        checkout_layout = QVBoxLayout(checkout_section)
        checkout_layout.setSpacing(8)
        checkout_layout.setContentsMargins(10, 10, 10, 10)
        
        checkout_header = QLabel("🚪 CHECK OUT - VEHICLE EXIT")
        checkout_header.setFont(QFont("Arial", 10, QFont.Bold))
        checkout_header.setAlignment(Qt.AlignCenter)
        checkout_header.setStyleSheet(
            "background-color: #dc2626; color: white; padding: 8px; border-radius: 5px; "
            "font-weight: bold; letter-spacing: 0.5px;"
        )
        checkout_layout.addWidget(checkout_header)
        
        # License Plate input
        plate_layout = QHBoxLayout()
        plate_label = QLabel("License Plate")
        plate_label.setFont(QFont("Arial", 9, QFont.Bold))
        plate_label.setMinimumWidth(120)
        plate_label.setStyleSheet("color: #374151;")
        plate_layout.addWidget(plate_label)
        self.checkout_plate_input = QLineEdit()
        self.checkout_plate_input.setPlaceholderText("Enter license plate...")
        self.checkout_plate_input.setMinimumHeight(32)
        self.checkout_plate_input.setStyleSheet(
            "border: 2px solid #d1d5db; border-radius: 5px; padding: 6px; background-color: #f9fafb;"
            "QLineEdit:focus { border: 2px solid #dc2626; background-color: white; }"
        )
        plate_layout.addWidget(self.checkout_plate_input)
        checkout_layout.addLayout(plate_layout)
        
        checkout_section.setStyleSheet(
            "background-color: white; border: 1px solid #e5e7eb; border-radius: 6px;"
        )
        scroll_layout.addWidget(checkout_section)
        
        # Check-out button
        self.checkout_btn = self._create_button(
            "🏁 CHECK OUT (OUT)",
            "#dc2626",
            "#b91c1c",
            42,
            self.check_out
        )
        scroll_layout.addWidget(self.checkout_btn)
        
        # ============ SECTION 3: TRANSACTION INFO ============
        info_header = QLabel("💳 TRANSACTION INFORMATION")
        info_header.setFont(QFont("Arial", 10, QFont.Bold))
        info_header.setAlignment(Qt.AlignCenter)
        info_header.setStyleSheet(
            "background-color: #1f2937; color: white; padding: 10px; border-radius: 6px; "
            "font-weight: bold; letter-spacing: 1px;"
        )
        scroll_layout.addWidget(info_header)
        
        # Status message
        self.status_label = QLabel("System Ready")
        self.status_label.setFont(QFont("Arial", 9))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "background-color: #f0fdf4; color: #166534; padding: 12px; border-radius: 6px; "
            "border: 2px solid #bbf7d0; font-weight: 500;"
        )
        self.status_label.setMinimumHeight(45)
        scroll_layout.addWidget(self.status_label)
        
        # Fee display - Eye-catching
        self.fee_label = QLabel("💰 PARKING FEE\n0 VND")
        self.fee_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.fee_label.setAlignment(Qt.AlignCenter)
        self.fee_label.setStyleSheet(
            "background-color: #fef3c7; color: #92400e; padding: 15px; border-radius: 6px; "
            "border: 2px solid #fcd34d; font-weight: bold; letter-spacing: 1px;"
        )
        self.fee_label.setMinimumHeight(60)
        scroll_layout.addWidget(self.fee_label)
        
        # ============ SECTION 4: PARKING RECORDS TABLE ============
        table_header = QLabel("📊 PARKING RECORDS & HISTORY")
        table_header.setFont(QFont("Arial", 10, QFont.Bold))
        table_header.setAlignment(Qt.AlignCenter)
        table_header.setStyleSheet(
            "background-color: #1e3a8a; color: white; padding: 10px; border-radius: 6px; "
            "font-weight: bold; letter-spacing: 1px;"
        )
        scroll_layout.addWidget(table_header)
        
        # Table with professional styling
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            'Card ID', 'License Plate', 'Time In', 'Time Out', 'Slot', 'Status', 'Fee (VND)'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setRowCount(0)
        self.table.setMinimumHeight(150)
        self.table.setMaximumHeight(250)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f3f4f6;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1e40af;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        scroll_layout.addWidget(self.table)
        
        # ============ SECTION 5: DATA EXPORT ============
        export_header = QLabel("📥 DATA MANAGEMENT")
        export_header.setFont(QFont("Arial", 10, QFont.Bold))
        export_header.setAlignment(Qt.AlignCenter)
        export_header.setStyleSheet(
            "background-color: #7c3aed; color: white; padding: 8px; border-radius: 6px; "
            "font-weight: bold; margin-top: 5px;"
        )
        scroll_layout.addWidget(export_header)
        
        # Download Excel button
        self.download_btn = self._create_button(
            "💾 DOWNLOAD EXCEL REPORT",
            "#7c3aed",
            "#6d28d9",
            40,
            self.export_to_excel
        )
        scroll_layout.addWidget(self.download_btn)
        
        scroll_layout.addStretch()
        right_layout.addLayout(scroll_layout)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 0)
        main_layout.addWidget(right_panel, 1)
    
    def _create_button(self, text, bg_color, hover_color, height, callback):
        """Create a professional button with consistent styling"""
        btn = QPushButton(text)
        btn.setMinimumHeight(height)
        btn.setFont(QFont("Arial", 9, QFont.Bold))
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {bg_color};"
            f"  color: white;"
            f"  font-weight: bold;"
            f"  border-radius: 6px;"
            f"  border: none;"
            f"  padding: 8px;"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {hover_color};"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background-color: {hover_color};"
            f"  padding: 10px 8px 6px 8px;"
            f"}}"
        )
        btn.clicked.connect(callback)
        return btn
    
    def _refresh_ports(self):
        """Auto-detect and populate available serial ports"""
        self.port_combo.clear()
        ports = get_available_ports()
        
        if ports:
            for port_name, port_desc in ports:
                self.port_combo.addItem(f"{port_name} - {port_desc}", port_name)
        else:
            self.port_combo.addItem("No ports found", None)
    
    def toggle_serial_connection(self):
        """Toggle serial port connection - Connect or disconnect from Arduino/ESP32"""
        if self.serial_connected:
            # Disconnect from serial port
            if self.serial_thread:
                self.serial_thread.stop()
                self.serial_thread.join(timeout=2)
                self.serial_thread = None
            self.serial_connected = False
            self.on_serial_status_changed(False, "Disconnected")
        else:
            # Connect to selected serial port
            port_name = self.port_combo.currentData()
            baud_rate = int(self.baud_combo.currentText())
            
            if not port_name:
                QMessageBox.warning(self, "Error", "No serial port selected")
                return
            
            # Create and start serial worker thread
            self.serial_thread = SerialWorker(self.serial_signals)
            self.serial_thread.set_connection(port_name, baud_rate)
            self.serial_thread.start()
            self.serial_connected = True
    
    def on_serial_status_changed(self, connected, message):
        """Update serial connection status indicator in UI"""
        self.serial_connected = connected
        
        if connected:
            # Show connected status (green indicator)
            self.serial_status_label.setText("🟢 Connected")
            self.serial_status_label.setStyleSheet("color: #059669; font-weight: bold;")
            self.serial_connect_btn.setText("🔌 DISCONNECT")
            self.serial_connect_btn.setStyleSheet(
                "QPushButton { background-color: #dc2626; color: white; font-weight: bold; "
                "border-radius: 6px; border: none; padding: 6px; }"
                "QPushButton:hover { background-color: #b91c1c; }"
            )
            print(f"✓ {message}")
        else:
            # Show disconnected status (red indicator)
            self.serial_status_label.setText("🔴 Disconnected")
            self.serial_status_label.setStyleSheet("color: #dc2626; font-weight: bold;")
            self.serial_connect_btn.setText("🔗 CONNECT")
            self.serial_connect_btn.setStyleSheet(
                "QPushButton { background-color: #2563eb; color: white; font-weight: bold; "
                "border-radius: 6px; border: none; padding: 6px; }"
                "QPushButton:hover { background-color: #1d4ed8; }"
            )
            if message != "Disconnected":
                print(f"✗ {message}")
    
    def on_serial_error(self, error_msg):
        """Handle and display serial port errors"""
        print(f"❌ Serial Error: {error_msg}")
        self.status_label.setText(f"Status: Serial Error - {error_msg}")
    
    def on_card_scanned(self, card_data):
        """Handle card scan event from Arduino/ESP32 RFID reader
        
        Expected JSON format:
        {"event":"CARD_SCAN","uid":"A1B2C3D4","gate":"ENTRY","slot":1}
        
        Process:
        1. Store card data temporarily
        2. Trigger license plate capture
        3. Wait for OCR extraction to complete
        4. Auto check-in/out based on gate field
        """
        try:
            # Prevent concurrent card processing
            if self.is_processing_card:
                print("⚠️  Already processing a card scan, skipping...")
                return
            
            self.is_processing_card = True
            
            # Extract card data from JSON
            card_id = card_data.get('uid', '').strip()
            gate = card_data.get('gate', 'ENTRY').upper()  # ENTRY or EXIT
            slot = card_data.get('slot', '')
            
            # Validate card data
            if not card_id:
                self.status_label.setText("Status: Invalid card ID received")
                self.is_processing_card = False
                return
            
            # Store card data for later use
            self.pending_card_data = {
                'card_id': card_id,
                'gate': gate,
                'slot': str(slot) if slot else ''
            }
            
            # Auto-fill the card ID and slot fields
            self.card_id_input.setText(card_id)
            if self.pending_card_data['slot']:
                self.slot_input.setText(self.pending_card_data['slot'])
            
            # Update status to show card received
            self.status_label.setText(f"Status: Card scanned ({card_id}) - {gate} | Capturing license plate...")
            print(f"\n📱 Card event received: ID={card_id}, Gate={gate}, Slot={slot}")
            
            # Trigger license plate capture after small delay
            QTimer.singleShot(200, self._process_card_capture)
        
        except Exception as e:
            self.status_label.setText(f"Status: Error processing card data - {str(e)}")
            print(f"❌ Card processing error: {e}")
            self.is_processing_card = False
    
    def _process_card_capture(self):
        """Capture license plate for the pending card scan"""
        if not self.pending_card_data or self.current_frame is None:
            self.status_label.setText("Status: No frame available for capture")
            self.is_processing_card = False
            return
        
        try:
            # Check if YOLO model is loaded
            if not self.camera_thread.license_plate_detector:
                self.status_label.setText("Status: YOLO model not ready")
                self.is_processing_card = False
                return
            
            # Run YOLO detection on current frame
            detections = self.camera_thread.license_plate_detector(self.current_frame)[0]
            
            if len(detections.boxes) == 0:
                self.status_label.setText(f"Status: No license plate detected for {self.pending_card_data['card_id']}")
                print(f"⚠️  No plate detected for card {self.pending_card_data['card_id']}")
                self.is_processing_card = False
                return
            
            # Extract first detection bounding box
            detection = detections.boxes.data.tolist()[0]
            x1, y1, x2, y2, score, class_id = detection
            
            # Crop license plate region
            crop = self.current_frame[int(y1):int(y2), int(x1):int(x2), :]
            
            # Display snapshot (cropped license plate)
            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_crop.shape
            bytes_per_line = 3 * w
            qt_image = QImage(rgb_crop.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaledToWidth(380, Qt.SmoothTransformation)
            self.snapshot_label.setPixmap(scaled_pixmap)
            
            # Save captured images to disk
            try:
                captured_dir = Path(__file__).parent / "captured_images"
                captured_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                
                # Save full frame
                full_frame_path = captured_dir / f"full_frame_{timestamp}.jpg"
                cv2.imwrite(str(full_frame_path), self.current_frame)
                
                # Save cropped license plate
                crop_path = captured_dir / f"license_plate_{timestamp}.jpg"
                cv2.imwrite(str(crop_path), crop)
                
                print(f"✓ Captured images saved: {timestamp}")
            except Exception as save_error:
                print(f"⚠️  Could not save images: {save_error}")
            
            # Run OCR to extract license plate text
            self.status_label.setText(f"Status: Extracting text for {self.pending_card_data['card_id']}...")
            plate_text, conf = extract_license_plate(crop)
            
            if not plate_text:
                self.status_label.setText(f"Status: OCR failed for {self.pending_card_data['card_id']} - no text extracted")
                self.extracted_plate_label.setText("OCR Failed")
                print(f"❌ OCR extraction failed for card {self.pending_card_data['card_id']}")
                self.is_processing_card = False
                return
            
            # Successfully extracted license plate
            self.captured_license_plate = plate_text
            self.extracted_plate_label.setText(plate_text)
            self.extracted_plate_label.setStyleSheet(
                "background-color: #f3e8ff; color: #6d28d9; padding: 10px; "
                "border-radius: 6px; border: 2px solid #7c3aed; letter-spacing: 2px; "
                "font-size: 16pt; font-weight: bold;"
            )
            
            print(f"✅ License plate extracted: {plate_text} (Confidence: {conf:.2%})")
            
            # Now perform auto check-in or check-out based on gate
            gate = self.pending_card_data['gate']
            
            # Show confirmation dialog before proceeding
            if gate == "ENTRY":
                self.status_label.setText(f"Status: Waiting for confirmation...")
                QTimer.singleShot(300, self._show_checkin_confirmation)
            elif gate == "EXIT":
                self.status_label.setText(f"Status: Waiting for confirmation...")
                QTimer.singleShot(300, self._show_checkout_confirmation)
            else:
                self.status_label.setText(f"Status: Unknown gate type: {gate}")
                self.is_processing_card = False
        
        except Exception as e:
            self.status_label.setText(f"Status: Capture error - {str(e)}")
            print(f"❌ Capture error: {e}")
            self.is_processing_card = False
    
    def _show_checkin_confirmation(self):
        """Show confirmation dialog for check-in from RFID card"""
        if not self.pending_card_data or not self.captured_license_plate:
            self.is_processing_card = False
            return
        
        card_id = self.pending_card_data['card_id']
        slot = self.pending_card_data['slot']
        plate = self.captured_license_plate
        
        # Create detailed confirmation message
        msg_text = (
            f"<b>✓ LICENSE PLATE DETECTED</b><br><br>"
            f"<b>Card ID:</b> {card_id}<br>"
            f"<b>License Plate:</b> {plate}<br>"
            f"<b>Parking Slot:</b> {slot}<br>"
            f"<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}<br><br>"
            f"<b>Do you want to CHECK IN this vehicle?</b>"
        )
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "🚗 CHECK IN CONFIRMATION",
            msg_text,
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok
        )
        
        if reply == QMessageBox.Ok:
            # Proceed with check-in
            QTimer.singleShot(100, self._auto_check_in)
        else:
            # User cancelled
            self.status_label.setText("Status: Check-in cancelled by user")
            print(f"⚠️  Check-in cancelled for card {card_id}")
            self.pending_card_data = None
            self.is_processing_card = False
    
    def _show_checkout_confirmation(self):
        """Show confirmation dialog for check-out from RFID card"""
        if not self.pending_card_data or not self.captured_license_plate:
            self.is_processing_card = False
            return
        
        card_id = self.pending_card_data['card_id']
        plate = self.captured_license_plate
        
        # Find the record to show duration
        record = None
        for r in self.parking_records:
            if r['license_plate'] == plate and r['status'] == 'IN':
                record = r
                break
        
        duration_str = ""
        if record:
            time_in = record['time_in']
            time_out = datetime.now()
            duration = time_out - time_in
            hours = duration.total_seconds() / 3600
            duration_str = f"<b>Duration:</b> {hours:.2f} hours<br>"
        
        # Create detailed confirmation message
        msg_text = (
            f"<b>✓ LICENSE PLATE DETECTED</b><br><br>"
            f"<b>Card ID:</b> {card_id}<br>"
            f"<b>License Plate:</b> {plate}<br>"
            f"{duration_str}"
            f"<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}<br><br>"
            f"<b>Do you want to CHECK OUT this vehicle?</b>"
        )
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "🚪 CHECK OUT CONFIRMATION",
            msg_text,
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok
        )
        
        if reply == QMessageBox.Ok:
            # Proceed with check-out
            QTimer.singleShot(100, self._auto_check_out)
        else:
            # User cancelled
            self.status_label.setText("Status: Check-out cancelled by user")
            print(f"⚠️  Check-out cancelled for card {card_id}")
            self.pending_card_data = None
            self.is_processing_card = False
    
    def _auto_check_in(self):
        """Auto check-in after successful license plate extraction"""
        try:
            if not self.pending_card_data:
                self.is_processing_card = False
                return
            
            card_id = self.pending_card_data['card_id']
            slot = self.pending_card_data['slot']
            
            if not card_id or not slot:
                self.status_label.setText("Status: Missing card ID or slot for check-in")
                self.is_processing_card = False
                return
            
            # Check if already checked in
            for record in self.parking_records:
                if record['card_id'] == card_id and record['status'] == 'IN':
                    self.status_label.setText(f"Status: {card_id} already checked in at slot {record['slot']}")
                    print(f"⚠️  Card {card_id} already checked in")
                    self.is_processing_card = False
                    return
            
            now = datetime.now()
            
            # Create new parking record
            record = {
                'card_id': card_id,
                'license_plate': self.captured_license_plate,  # Use extracted plate
                'time_in': now,
                'time_out': None,
                'slot': slot,
                'status': 'IN',
                'fee': 0
            }
            
            self.parking_records.append(record)
            self._save_to_csv(record)
            self.update_table()
            
            msg = f"✅ CHECK IN SUCCESSFUL\n\nCard ID: {card_id}\nLicense Plate: {self.captured_license_plate}\nSlot: {slot}"
            print(f"\n✅ AUTO CHECK-IN: {card_id} | Plate: {self.captured_license_plate} | Slot: {slot} | Time: {now.strftime('%H:%M:%S')}")
            self.status_label.setText(f"Status: ✓ {card_id} checked in successfully")
            
            # Clear temporary data
            self.pending_card_data = None
            self.is_processing_card = False
            
        except Exception as e:
            self.status_label.setText(f"Status: Auto check-in error - {str(e)}")
            print(f"❌ Auto check-in error: {e}")
            self.is_processing_card = False
    
    def _auto_check_out(self):
        """Auto check-out after successful license plate extraction"""
        try:
            if not self.pending_card_data or not self.captured_license_plate:
                self.is_processing_card = False
                return
            
            license_plate = self.captured_license_plate.upper()
            card_id = self.pending_card_data['card_id']
            
            # Find existing record
            record = None
            for r in self.parking_records:
                if r['license_plate'] == license_plate:
                    record = r
                    break
            
            if not record:
                self.status_label.setText(f"Status: No vehicle with plate {license_plate} found")
                print(f"❌ License plate {license_plate} not found in records")
                self.is_processing_card = False
                return
            
            # Check if already checked out
            if record['status'] == 'OUT':
                self.status_label.setText(f"Status: Vehicle {license_plate} already checked out")
                self.is_processing_card = False
                return
            
            # Calculate parking fee
            time_in = record['time_in']
            time_out = datetime.now()
            duration = time_out - time_in
            hours = duration.total_seconds() / 3600
            
            # Fee calculation: < 2h = 20000 VND, +10000 per extra hour
            if hours <= 2:
                fee = 20000
            else:
                fee = 20000 + int((hours - 2) * 10000)
            
            # Update record with checkout info
            record['time_out'] = time_out
            record['status'] = 'OUT'
            record['fee'] = fee
            
            self._save_to_csv(record)
            self.update_table()
            
            self.fee_label.setText(f"💰 PARKING FEE\n{fee:,} VND")
            
            print(f"\n✅ AUTO CHECK-OUT: {license_plate} | Card: {card_id} | Slot: {record['slot']} | Fee: {fee:,} VND | Duration: {hours:.2f}h")
            self.status_label.setText(f"Status: ✓ {license_plate} checked out | Fee: {fee:,} VND")
            
            # Clear temporary data
            self.pending_card_data = None
            self.is_processing_card = False
            
        except Exception as e:
            self.status_label.setText(f"Status: Auto check-out error - {str(e)}")
            print(f"❌ Auto check-out error: {e}")
            self.is_processing_card = False
    
    def on_frame_received(self, frame):
        """Display incoming camera frame in UI"""
        self.current_frame = frame
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = 3 * w
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled = pixmap.scaledToWidth(700, Qt.SmoothTransformation)
            self.camera_label.setPixmap(scaled)
        except Exception as e:
            print(f"Frame display error: {e}")
    
    def on_camera_error(self, msg):
        """Handle and display camera errors to user"""
        print(f"❌ Camera Error: {msg}")
        self.status_label.setText(f"Status: Camera Error - {msg}")
    
    def capture_plate(self):
        """Manually capture current frame and extract license plate via YOLO + OCR"""
        if self.current_frame is None:
            QMessageBox.warning(self, "Error", "No frame to capture")
            return
        
        try:
            if not self.camera_thread.license_plate_detector:
                QMessageBox.warning(self, "Error", "YOLO model not loaded")
                return
            
            self.status_label.setText("Status: Processing...")
            
            # YOLO detection
            detections = self.camera_thread.license_plate_detector(self.current_frame)[0]
            
            if len(detections.boxes) == 0:
                QMessageBox.information(self, "Result", "No license plate detected")
                self.status_label.setText("Status: No plate detected")
                return
            
            # Get first detection
            detection = detections.boxes.data.tolist()[0]
            x1, y1, x2, y2, score, class_id = detection
            
            # Crop license plate area
            crop = self.current_frame[int(y1):int(y2), int(x1):int(x2), :]
            
            # Display snapshot (cropped license plate image)
            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_crop.shape
            bytes_per_line = 3 * w
            qt_image = QImage(rgb_crop.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaledToWidth(380, Qt.SmoothTransformation)
            self.snapshot_label.setPixmap(scaled_pixmap)
            
            # Save FULL FRAME (entire video capture) to captured_images folder
            try:
                # Create captured_images directory if it doesn't exist
                captured_dir = Path(__file__).parent / "captured_images"
                captured_dir.mkdir(exist_ok=True)
                
                # Generate unique filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Remove last 3 digits for milliseconds
                
                # Save FULL FRAME (entire screenshot with entire vehicle/parking area)
                full_frame_filename = f"full_frame_{timestamp}.jpg"
                full_frame_path = captured_dir / full_frame_filename
                cv2.imwrite(str(full_frame_path), self.current_frame)
                print(f"✓ Full frame saved: {full_frame_path}")
                
                # Also save cropped license plate (for reference/verification)
                crop_filename = f"license_plate_{timestamp}.jpg"
                crop_path = captured_dir / crop_filename
                cv2.imwrite(str(crop_path), crop)
                print(f"✓ License plate crop saved: {crop_path}")
            except Exception as save_error:
                print(f"Warning: Could not save images: {save_error}")
            
            # OCR extraction
            plate_text, conf = extract_license_plate(crop)
            
            if not plate_text:
                QMessageBox.information(self, "Result", "Could not extract license plate text")
                self.status_label.setText("Status: OCR failed - no text recognized")
                self.extracted_plate_label.setText("OCR Failed")
                return
            
            # Store the extracted license plate
            self.captured_license_plate = plate_text
            
            # Display extracted license plate (purple box)
            self.extracted_plate_label.setText(plate_text)
            self.extracted_plate_label.setStyleSheet(
                "background-color: #f3e8ff; color: #6d28d9; padding: 10px; "
                "border-radius: 6px; border: 2px solid #7c3aed; letter-spacing: 2px; "
                "font-size: 16pt; font-weight: bold;"
            )
            
            # Update status
            self.status_label.setText(f"Status: ✓ License plate captured - {plate_text}")
            
            print(f"\n✅ License Plate Captured: {plate_text} (Confidence: {conf:.2%})")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Capture error: {str(e)}")
            print(f"Capture error: {e}")
            import traceback
            traceback.print_exc()
    
    def check_in(self):
        """Manual check-in: Record vehicle entry with card ID, slot, and captured license plate"""
        card_id = self.card_id_input.text().strip()
        slot = self.slot_input.text().strip()
        
        if not card_id or not slot:
            QMessageBox.warning(self, "Error", "Please enter Card ID and Slot Number")
            return
        
        if not self.captured_license_plate:
            QMessageBox.warning(self, "Error", "Please capture license plate first")
            return
        
        # Check if vehicle already checked in
        for record in self.parking_records:
            if record['card_id'] == card_id and record['status'] == 'IN':
                QMessageBox.warning(self, "Error", f"Vehicle already checked in at slot {record['slot']}")
                return
        
        now = datetime.now()
        
        # Show confirmation dialog
        msg_text = (
            f"<b>✓ CONFIRM CHECK IN</b><br><br>"
            f"<b>Card ID:</b> {card_id}<br>"
            f"<b>License Plate:</b> {self.captured_license_plate}<br>"
            f"<b>Parking Slot:</b> {slot}<br>"
            f"<b>Time:</b> {now.strftime('%H:%M:%S')}<br><br>"
            f"<b>Do you want to proceed?</b>"
        )
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "🚗 CHECK IN CONFIRMATION",
            msg_text,
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok
        )
        
        if reply != QMessageBox.Ok:
            self.status_label.setText("Status: Check-in cancelled by user")
            print(f"⚠️  Check-in cancelled for card {card_id}")
            return
        
        # Create new parking record with captured license plate
        record = {
            'card_id': card_id,
            'license_plate': self.captured_license_plate,  # Use extracted license plate from OCR
            'time_in': now,
            'time_out': None,
            'slot': slot,
            'status': 'IN',
            'fee': 0
        }
        
        self.parking_records.append(record)
        
        # Save record to CSV
        self._save_to_csv(record)
        
        # Refresh table display
        self.update_table()
        
        # Show success message
        msg = f"✅ Check-in Successful\n\nCard ID: {card_id}\nLicense Plate: {self.captured_license_plate}\nSlot: {slot}\nTime: {now.strftime('%H:%M:%S')}"
        QMessageBox.information(self, "Check-in Success", msg)
        
        self.status_label.setText(f"Status: Checked in - Card {card_id}, Plate {self.captured_license_plate}")
        
        # Clear input fields for next transaction
        self.card_id_input.clear()
        self.slot_input.clear()
        
        print(f"\n✅ CHECK IN - Card: {card_id}, Slot: {slot}, Plate: {self.captured_license_plate}, Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def check_out(self):
        """Manual check-out: Record vehicle exit, calculate fee, and update status"""
        license_plate = self.checkout_plate_input.text().strip().upper()
        
        if not license_plate:
            QMessageBox.warning(self, "Error", "Please enter License Plate")
            return
        
        # Search for vehicle record by license plate
        record = None
        for r in self.parking_records:
            if r['license_plate'] == license_plate:
                record = r
                break
        
        if not record:
            msg = "❌ No vehicle with the above license plate was found."
            QMessageBox.warning(self, "Not Found", msg)
            print(f"❌ License plate not found: {license_plate}")
            return
        
        # Check if already checked out
        if record['status'] == 'OUT':
            QMessageBox.warning(self, "Error", "Vehicle already checked out")
            return
        
        # Calculate parking duration and fee
        time_in = record['time_in']
        time_out = datetime.now()
        duration = time_out - time_in
        hours = duration.total_seconds() / 3600
        
        # Fee structure: < 2 hours = 20000 VND, +10000 VND per additional hour
        if hours <= 2:
            fee = 20000
        else:
            fee = 20000 + int((hours - 2) * 10000)
        
        # Show confirmation dialog
        msg_text = (
            f"<b>✓ CONFIRM CHECK OUT</b><br><br>"
            f"<b>License Plate:</b> {license_plate}<br>"
            f"<b>Parking Slot:</b> {record['slot']}<br>"
            f"<b>Parking Duration:</b> {hours:.2f} hours<br>"
            f"<b>Parking Fee:</b> {fee:,} VND<br>"
            f"<b>Time:</b> {time_out.strftime('%H:%M:%S')}<br><br>"
            f"<b>Do you want to proceed?</b>"
        )
        
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "🚪 CHECK OUT CONFIRMATION",
            msg_text,
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok
        )
        
        if reply != QMessageBox.Ok:
            self.status_label.setText("Status: Check-out cancelled by user")
            print(f"⚠️  Check-out cancelled for plate {license_plate}")
            return
        
        # Update record with checkout information
        record['time_out'] = time_out
        record['status'] = 'OUT'
        record['fee'] = fee
        
        # Save to CSV file
        self._save_to_csv(record)
        
        # Refresh table display
        self.update_table()
        
        # Show success message
        msg = f"✅ Check-out Successful\n\nLicense Plate: {license_plate}\nSlot: {record['slot']}\nFee: {fee:,} VND\nDuration: {hours:.2f} hours"
        QMessageBox.information(self, "Check-out Success", msg)
        
        # Update status and fee display
        self.status_label.setText(f"Status: Vehicle {license_plate} checked out | Parking slot: {record['slot']}")
        self.fee_label.setText(f"💰 PARKING FEE\n{fee:,} VND")
        self.checkout_plate_input.clear()
        
        print(f"\n✅ CHECK OUT - Plate: {license_plate}, Slot: {record['slot']}, Fee: {fee:,} VND")
    
    def update_slot_status(self):
        """Update parking slot display based on current records"""
        # Clear all slots (set to empty/green)
        for slot_info in self.slot_buttons:
            slot_num = slot_info['slot_num']
            slot_info['is_occupied'] = False
            slot_info['button'].setStyleSheet(
                "QPushButton {"
                "  background-color: #10b981;"
                "  color: white;"
                "  font-weight: bold;"
                "  border-radius: 6px;"
                "  border: 2px solid #059669;"
                "  padding: 6px;"
                "}"
                "QPushButton:hover {"
                "  background-color: #059669;"
                "}"
            )
        
        # Mark occupied slots (red) for vehicles currently parked
        for record in self.parking_records:
            if record['status'] == 'IN':  # Vehicle is currently parked
                slot_num = int(record['slot'])
                if 1 <= slot_num <= 12:
                    for slot_info in self.slot_buttons:
                        if slot_info['slot_num'] == slot_num:
                            slot_info['is_occupied'] = True
                            slot_info['button'].setStyleSheet(
                                "QPushButton {"
                                "  background-color: #ef4444;"
                                "  color: white;"
                                "  font-weight: bold;"
                                "  border-radius: 6px;"
                                "  border: 2px solid #dc2626;"
                                "  padding: 6px;"
                                "}"
                                "QPushButton:hover {"
                                "  background-color: #dc2626;"
                                "}"
                            )
                            break
    
    def update_table(self):
        """Refresh parking records table with current data"""
        self.table.setRowCount(0)
        
        for i, record in enumerate(self.parking_records):
            self.table.insertRow(i)
            
            # Populate table cells
            self.table.setItem(i, 0, QTableWidgetItem(record['card_id']))
            self.table.setItem(i, 1, QTableWidgetItem(record['license_plate']))
            self.table.setItem(i, 2, QTableWidgetItem(record['time_in'].strftime("%H:%M:%S") if record['time_in'] else ""))
            self.table.setItem(i, 3, QTableWidgetItem(record['time_out'].strftime("%H:%M:%S") if record['time_out'] else ""))
            self.table.setItem(i, 4, QTableWidgetItem(record['slot']))
            
            # Color-code status column
            status_item = QTableWidgetItem(record['status'])
            if record['status'] == 'IN':
                status_item.setBackground(QColor("#d4edda"))  # Green for entry
            else:
                status_item.setBackground(QColor("#f8d7da"))  # Red for exit
            self.table.setItem(i, 5, status_item)
            
            # Display fee if checkout occurred
            self.table.setItem(i, 6, QTableWidgetItem(str(record['fee']) if record['fee'] > 0 else ""))
        
        # Update parking slots display based on current records
        self.update_slot_status()
    
    def _save_to_csv(self, record):
        """Append parking record to CSV file"""
        try:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    record['card_id'],
                    record['license_plate'],
                    record['time_in'].strftime("%Y-%m-%d %H:%M:%S") if record['time_in'] else "",
                    record['time_out'].strftime("%Y-%m-%d %H:%M:%S") if record['time_out'] else "",
                    record['slot'],
                    record['status'],
                    record['fee'] if record['fee'] > 0 else ""
                ])
        except Exception as e:
            print(f"❌ Error saving to CSV: {e}")
    
    def export_to_excel(self):
        """Export all parking records to Excel file with formatting"""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            
            # Get file path from dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Parking Records to Excel", 
                f"parking_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Ensure .xlsx extension
            if not file_path.endswith('.xlsx'):
                file_path = file_path + '.xlsx'
            
            # Create workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Parking Records"
            
            # Add metadata
            ws['A1'].value = "Parking Management System - Records Export"
            ws['A2'].value = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ws['A2'].font = Font(italic=True, size=9)
            ws['A3'].value = f"Total Records: {len(self.parking_records)}"
            ws['A3'].font = Font(bold=True, size=10)
            
            # Headers (starting from row 5)
            headers = ['Card ID', 'License Plate', 'Time In', 'Time Out', 'Slot', 'Status', 'Fee (VND)']
            ws.append([])  # Row 4 - blank
            ws.append(headers)  # Row 5
            
            # Header style
            header_fill = PatternFill(start_color="1e40af", end_color="1e40af", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for cell in ws[5]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = thin_border
            
            # Add data rows
            for record in self.parking_records:
                time_in_str = record['time_in'].strftime("%Y-%m-%d %H:%M:%S") if record['time_in'] else ""
                time_out_str = record['time_out'].strftime("%Y-%m-%d %H:%M:%S") if record['time_out'] else ""
                fee_str = f"{record['fee']:,}" if record['fee'] > 0 else ""
                
                row = [
                    record['card_id'],
                    record['license_plate'],
                    time_in_str,
                    time_out_str,
                    record['slot'],
                    record['status'],
                    fee_str
                ]
                ws.append(row)
            
            # Format data cells
            for row in ws.iter_rows(min_row=6, max_row=ws.max_row, min_col=1, max_col=7):
                for cell in row:
                    cell.border = thin_border
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                    
                    # Format fee column (right-align for numbers)
                    if cell.column == 7:  # Fee column
                        cell.alignment = Alignment(horizontal='right', vertical='center')
                    
                    # Color status cells
                    if cell.column == 6:  # Status column
                        if cell.value == 'IN':
                            cell.fill = PatternFill(start_color="d4edda", end_color="d4edda", fill_type="solid")
                            cell.font = Font(bold=True, color="155724")
                        elif cell.value == 'OUT':
                            cell.fill = PatternFill(start_color="f8d7da", end_color="f8d7da", fill_type="solid")
                            cell.font = Font(bold=True, color="721c24")
            
            # Set column widths for better readability
            ws.column_dimensions['A'].width = 15
            ws.column_dimensions['B'].width = 20
            ws.column_dimensions['C'].width = 22
            ws.column_dimensions['D'].width = 22
            ws.column_dimensions['E'].width = 12
            ws.column_dimensions['F'].width = 12
            ws.column_dimensions['G'].width = 18
            
            # Freeze header row for easier scrolling
            ws.freeze_panes = 'A6'
            
            # Save the workbook to file
            wb.save(file_path)
            
            # Calculate summary statistics
            total_in = sum(1 for r in self.parking_records if r['status'] == 'IN')
            total_out = sum(1 for r in self.parking_records if r['status'] == 'OUT')
            total_fee = sum(r['fee'] for r in self.parking_records if r['fee'] > 0)
            
            # Show success message
            success_msg = (
                f"✅ Excel file saved successfully!\n\n"
                f"File: {file_path}\n"
                f"Total Records: {len(self.parking_records)}\n"
                f"Vehicles IN: {total_in}\n"
                f"Vehicles OUT: {total_out}\n"
                f"Total Revenue: {total_fee:,} VND"
            )
            QMessageBox.information(self, "Export Success", success_msg)
            print(f"✅ Exported to Excel: {file_path}")
            print(f"   Records: {len(self.parking_records)} | IN: {total_in} | OUT: {total_out} | Revenue: {total_fee:,} VND")
        
        except ImportError:
            QMessageBox.critical(
                self, 
                "Error", 
                "openpyxl module not installed.\n\n"
                "Please install it using:\n"
                "pip install openpyxl\n\n"
                "Or check requirements.txt and run:\n"
                "pip install -r requirements.txt"
            )
            print("❌ openpyxl not installed")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export Excel:\n\n{str(e)}")
            print(f"❌ Export error: {e}")
            import traceback
            traceback.print_exc()
    
    def closeEvent(self, event):
        """Clean up resources when application exits"""
        # Stop serial port thread
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.join(timeout=2)
        
        # Stop camera thread
        if self.camera_thread:
            self.camera_thread.stop()
        
        event.accept()


def main():
    """Main application entry point - Initialize PyQt5 application and show UI"""
    print("=" * 70)
    print("🅿️  PARKING MANAGEMENT SYSTEM")
    print("=" * 70)
    print()
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    try:
        # Create and display main window
        window = ParkingManagementUI()
        window.show()
        
        print("✓ Window displayed")
        print("✓ Application ready\n")
        
        # Start Qt event loop
        sys.exit(app.exec_())
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
