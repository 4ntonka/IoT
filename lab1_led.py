#!/usr/bin/env python3
"""
This script controls an LED on an Arduino board using serial communication.
"""

import serial
import time

# Serial port configuration
PORT = '/dev/ttyACM0'  # Adjust this based on your system
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
    ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
    while True:
        command = input("command > ").strip().lower()
        
        if command == 'on':
            print("LED on")
            send_command(on_command)
        elif command == 'off':
            print("LED off")
            send_command(off_command)
        elif command == 'blink':
            print("LED blink")
            send_command(blink_command)
        elif command == 'status':
            ser.write(status_command.encode())
            time.sleep(0.1)
            if ser.in_waiting > 0:
                state = ser.readline().decode().strip()
                if state == '0':
                    print("LED off")
                elif state == '1':
                    print("LED on")
                elif state == '2':
                    print("LED blink")
                else:
                    print(f"Unknown state: {state}")
        elif command in ['exit', 'quit']:
            print("Exiting program.")
            break
        else:
            print("Unknown command. Use: on, off, blink, status, exit, or quit.")
    ser.close()

if __name__ == "__main__":
    main()
