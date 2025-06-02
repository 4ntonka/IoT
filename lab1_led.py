#!/usr/bin/env python3
"""
This script controls an LED on an Arduino board using serial communication.
"""

import serial
import time

# Serial port configuration
PORT = '/dev/tty.usbmodem14101'  # Adjust this based on your system
BAUD_RATE = 9600

# LED commands
on_command = 'on\n'
off_command = 'off\n'
blink_command = 'blink\n'
status_command = 'status\n'

# Function to send a command to the Arduino
def send_command(command):
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        ser.write(command.encode())
        time.sleep(0.1)  # Wait for the Arduino to process the command
        ser.close()
    except serial.SerialException as e:
        print(f"Error: {e}")
        print("Make sure the Arduino is connected and the port is correct.")

# Main function
def main():
    print("Arduino LED Control")
    print("Commands: on, off, blink, status")
    
    while True:
        command = input("Enter command: ").strip().lower()
        
        if command == 'on':
            send_command(on_command)
        elif command == 'off':
            send_command(off_command)
        elif command == 'blink':
            send_command(blink_command)
        elif command == 'status':
            send_command(status_command)
        elif command in ['exit', 'quit']:
            print("Exiting program.")
            break
        else:
            print("Unknown command. Use: on, off, blink, status, exit, or quit.")

if __name__ == "__main__":
    main()
