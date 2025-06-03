"""
Accelerometer Sensor Module for Arduino Nano 33 IoT
Handles serial communication with the Arduino and processes accelerometer data

LSM6DS3 Accelerometer Specifications:
- Measurement range: ±2/±4/±8/±16 g (configurable)
- Sensitivity: 
  - ±2g scale: 0.061 mg/LSB (0.000061 g/LSB)
  - ±4g scale: 0.122 mg/LSB (0.000122 g/LSB)
  - ±8g scale: 0.244 mg/LSB (0.000244 g/LSB)
  - ±16g scale: 0.488 mg/LSB (0.000488 g/LSB)
- Output data rate: 1.6 Hz to 6.7 kHz

Our application uses the default ±2g scale, so values are represented with
4 decimal places to match the sensitivity of 0.061 mg/LSB.
"""

import serial
import serial.tools.list_ports
import time
import threading
import numpy as np


class AccelerometerSensor:
    """Class to handle accelerometer sensor data from Arduino"""
    
    def __init__(self, buffer_size=100):
        """Initialize the sensor with a buffer of specified size"""
        self._port = None
        self._serial = None
        self._connected = False
        self._reading = False
        self._buffer_size = buffer_size
        
        # Initialize data buffers with zeros
        self._x_data = np.zeros(buffer_size)
        self._y_data = np.zeros(buffer_size)
        self._z_data = np.zeros(buffer_size)
        
        # Latest readings
        self._x_latest = 0.0
        self._y_latest = 0.0
        self._z_latest = 0.0
        
        # Thread for reading data
        self._thread = None
        self._stop_event = threading.Event()
    
    @property
    def connected(self):
        """Check if the sensor is connected to a serial port"""
        return self._connected and self._serial is not None
    
    @property
    def reading(self):
        """Check if the sensor is currently reading data"""
        return self._reading
    
    @property
    def x_data(self):
        """Get the current X-axis accelerometer data buffer"""
        return self._x_data
    
    @property
    def y_data(self):
        """Get the current Y-axis accelerometer data buffer"""
        return self._y_data
    
    @property
    def z_data(self):
        """Get the current Z-axis accelerometer data buffer"""
        return self._z_data
    
    @property
    def latest_values(self):
        """Get the latest accelerometer readings"""
        return (self._x_latest, self._y_latest, self._z_latest)
    
    def list_ports(self):
        """List available serial ports"""
        ports = list(serial.tools.list_ports.comports())
        return [(p.device, p.description) for p in ports]
    
    def connect(self, port, baudrate=115200, timeout=1):
        """Connect to the specified serial port"""
        try:
            self._serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            # Flush any existing data to get fresh readings
            self._serial.reset_input_buffer()
            self._port = port
            self._connected = True
            return True
        except (serial.SerialException, ValueError) as e:
            print(f"Error connecting to {port}: {e}")
            self._connected = False
            self._serial = None
            return False
    
    def disconnect(self):
        """Disconnect from the serial port"""
        self.stop_reading()
        if self._serial is not None:
            self._serial.close()
        self._serial = None
        self._connected = False
    
    def _read_data(self):
        """Read data from the serial port in a separate thread"""
        while not self._stop_event.is_set():
            if not self._connected or self._serial is None:
                time.sleep(0.1)
                continue
            
            try:
                # Check if data is available
                if self._serial.in_waiting > 0:
                    line = self._serial.readline().decode('utf-8').strip()
                    parts = line.split(',')
                    if len(parts) == 3:
                        try:
                            x = float(parts[0])
                            y = float(parts[1])
                            z = float(parts[2])
                            
                            # Update latest values
                            self._x_latest = x
                            self._y_latest = y
                            self._z_latest = z
                            
                            # Shift data in the buffer
                            self._x_data = np.roll(self._x_data, -1)
                            self._y_data = np.roll(self._y_data, -1)
                            self._z_data = np.roll(self._z_data, -1)
                            
                            # Add new values at the end
                            self._x_data[-1] = x
                            self._y_data[-1] = y
                            self._z_data[-1] = z
                        except ValueError:
                            # Skip invalid data
                            pass
                
                # Small delay to prevent high CPU usage
                time.sleep(0.01)
                
            except Exception as e:
                print(f"Error reading data: {e}")
                self._connected = False
                break
    
    def start_reading(self):
        """Start reading data from the serial port"""
        if not self._connected:
            return False
        
        # Flush the buffer to get fresh readings
        self._serial.reset_input_buffer()
        
        # Reset the stop event
        self._stop_event.clear()
        
        # Start the reading thread
        self._thread = threading.Thread(target=self._read_data)
        self._thread.daemon = True
        self._thread.start()
        
        self._reading = True
        return True
    
    def stop_reading(self):
        """Stop reading data from the serial port"""
        if self._thread is not None and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=1.0)
        self._reading = False
    
    def flush_buffer(self):
        """Flush the serial input buffer to get fresh data"""
        if self._connected and self._serial is not None:
            self._serial.reset_input_buffer()
