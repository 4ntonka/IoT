"""
Accelerometer Sensor Module for Arduino Nano 33 IoT
Handles serial communication with the Arduino and processes accelerometer data

LSM6DS3 Accelerometer Specifications:
- Measurement range: ±2g (default configuration)
- Sensitivity: 0.061 mg/LSB (0.000061 g/LSB) at ±2g scale
- Output data rate: 20 Hz in our implementation

Values are represented with 4 decimal places to match the sensor sensitivity.
"""

import os
import csv
import time
import threading
import numpy as np
import serial
import serial.tools.list_ports


class AccelerometerSensor:
    """Class to handle accelerometer sensor data from Arduino Nano 33 IoT"""
    
    def __init__(self, buffer_size=100):
        """Initialize the sensor with a buffer of specified size
        
        Args:
            buffer_size: Number of samples to store in the buffer
        """
        # Connection properties
        self._port = None
        self._serial = None
        self._connected = False
        self._reading = False
        self._buffer_size = buffer_size
        
        # Data storage
        self._x_data = np.zeros(buffer_size)
        self._y_data = np.zeros(buffer_size)
        self._z_data = np.zeros(buffer_size)
        self._x_latest = 0.0
        self._y_latest = 0.0
        self._z_latest = 0.0
        
        # Threading control
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
        """Read data from the serial port in a background thread"""
        while not self._stop_event.is_set():
            # Skip if not connected
            if not self._connected or self._serial is None:
                time.sleep(0.1)
                continue
            
            try:
                # Process data if available
                if self._serial.in_waiting > 0:
                    self._process_serial_data()
                
                # Small delay to prevent high CPU usage
                time.sleep(0.01)
                
            except Exception as e:
                print(f"Error reading data: {e}")
                self._connected = False
                break
                
    def _process_serial_data(self):
        """Process a line of data from the serial port"""
        line = self._serial.readline().decode('utf-8').strip()
        parts = line.split(',')
        
        # Check if we have valid x,y,z data
        if len(parts) == 3:
            try:
                # Parse the values
                x, y, z = map(float, parts)
                
                # Update latest values
                self._x_latest, self._y_latest, self._z_latest = x, y, z
                
                # Update circular buffers
                for data, value in [(self._x_data, x), 
                                   (self._y_data, y), 
                                   (self._z_data, z)]:
                    data = np.roll(data, -1)
                    data[-1] = value
                
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
            
    def save_to_csv(self, filename):
        """Save current sensor data to a CSV file
        
        Args:
            filename: Path to the CSV file to save data to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            # Write data to CSV
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Sample', 'X', 'Y', 'Z'])  # Header
                
                # Use numpy's array capabilities for efficiency
                data = np.column_stack((
                    np.arange(len(self._x_data)),
                    self._x_data,
                    self._y_data,
                    self._z_data
                ))
                
                # Write all rows at once
                writer.writerows(data)
                    
            return True
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False
            
    @property
    def mean_values(self):
        """Calculate mean values for each axis
        
        Returns:
            tuple: (x_mean, y_mean, z_mean)
        """
        return (
            np.mean(self._x_data),
            np.mean(self._y_data),
            np.mean(self._z_data)
        )
        
    @property
    def std_values(self):
        """Calculate standard deviation values for each axis
        
        Returns:
            tuple: (x_std, y_std, z_std)
        """
        return (
            np.std(self._x_data),
            np.std(self._y_data),
            np.std(self._z_data)
        )
