#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Serial Port Tester for Parking Management System
Simulates Arduino/ESP32 RFID card scanner
"""

import serial
import json
import time
import sys

def list_ports():
    """List available serial ports"""
    import serial.tools.list_ports
    
    ports = []
    for port_info in serial.tools.list_ports.comports():
        ports.append((port_info.device, port_info.description))
    
    if ports:
        print("\nAvailable Serial Ports:")
        for i, (port, desc) in enumerate(ports, 1):
            print(f"  {i}. {port} - {desc}")
        return ports
    else:
        print("No serial ports found")
        return []

def send_card_scan(port_name, baud_rate, card_id, gate, slot):
    """Send a test card scan to parking system"""
    try:
        ser = serial.Serial(port_name, baud_rate, timeout=2)
        
        # Build JSON message
        data = {
            "event": "CARD_SCAN",
            "uid": card_id,
            "gate": gate,
            "slot": slot
        }
        
        # Send JSON
        json_str = json.dumps(data)
        ser.write((json_str + '\n').encode('utf-8'))
        
        print(f"✓ Sent: {json_str}")
        
        ser.close()
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Main test menu"""
    print("=" * 70)
    print("PARKING SYSTEM - SERIAL PORT TESTER")
    print("=" * 70)
    
    # List available ports
    ports = list_ports()
    if not ports:
        print("\nNo serial ports available. Connect Arduino/ESP32 and try again.")
        sys.exit(1)
    
    # Select port
    print("\nSelect serial port:")
    choice = input("Port number (1-{}): ".format(len(ports)))
    
    try:
        port_idx = int(choice) - 1
        if port_idx < 0 or port_idx >= len(ports):
            print("Invalid selection")
            sys.exit(1)
        port_name = ports[port_idx][0]
    except ValueError:
        print("Invalid input")
        sys.exit(1)
    
    # Select baud rate
    print("\nAvailable baud rates: 9600, 19200, 38400, 57600, 115200")
    baud_str = input("Baud rate (default 9600): ").strip()
    baud_rate = int(baud_str) if baud_str else 9600
    
    print(f"\n✓ Using {port_name} @ {baud_rate} baud")
    
    # Test menu
    while True:
        print("\n--- CARD SCAN SIMULATOR ---")
        print("1. Entry gate scan (test card)")
        print("2. Exit gate scan (test card)")
        print("3. Custom scan")
        print("4. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            send_card_scan(port_name, baud_rate, "A1B2C3D4", "ENTRY", 1)
            print("  (Slot 1, Entry gate)")
            time.sleep(0.5)
        
        elif choice == "2":
            send_card_scan(port_name, baud_rate, "A1B2C3D4", "EXIT", 1)
            print("  (Slot 1, Exit gate)")
            time.sleep(0.5)
        
        elif choice == "3":
            card_id = input("Card ID (hex string): ").strip().upper()
            gate = input("Gate (ENTRY/EXIT): ").strip().upper()
            slot = input("Slot number: ").strip()
            
            if gate in ["ENTRY", "EXIT"] and card_id and slot:
                send_card_scan(port_name, baud_rate, card_id, gate, int(slot))
            else:
                print("Invalid input")
            time.sleep(0.5)
        
        elif choice == "4":
            print("Goodbye!")
            break
        
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()
