#!/usr/bin/env python3
"""
Arduino Nano 33 IoT Accelerometer Data Visualization

A PyQt5 application for acquiring, visualizing, and analyzing accelerometer data
from an Arduino Nano 33 IoT board with the LSM6DS3 sensor.

Features:
- Real-time visualization of X, Y, Z acceleration data
- Configurable measurement duration
- Statistics calculation (mean, standard deviation)
- CSV data export
"""

import sys
import os
import time
import csv
import numpy as np
import serial
import serial.tools.list_ports
import matplotlib
matplotlib.use("Qt5Agg")

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer
from lab12_ui import Ui_Dialog

# PORT = '/dev/ttyACM0'
# BAUD_RATE = 9600
PORT = '/dev/cu.usbmodem21201'
BAUD_RATE = 115200


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
        self._buffer_size = buffer_size
        
        # Data storage
        self._x_data = np.zeros(buffer_size)
        self._y_data = np.zeros(buffer_size)
        self._z_data = np.zeros(buffer_size)
        self._x_latest = 0.0
        self._y_latest = 0.0
        self._z_latest = 0.0
        
    @property
    def connected(self):
        """Check if the sensor is connected to a serial port"""
        return self._connected and self._serial is not None
    
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
        if self._serial is not None:
            self._serial.close()
        self._serial = None
        self._connected = False
    
    def _read_data(self):
        """Read data from the serial port"""
        try:
            # Use non-blocking approach to readline
            line = self._serial.readline().decode('utf-8').strip()
            
            parts = line.split(',')
            
            # Check if we have valid x,y,z data
            if len(parts) == 3:
                try:
                    # Parse the values
                    x, y, z = map(float, parts)
                    
                    # Update latest values
                    self._x_latest, self._y_latest, self._z_latest = x, y, z
                    
                    # Update circular buffers and add new values at the end
                    self._x_data = np.roll(self._x_data, -1)
                    self._y_data = np.roll(self._y_data, -1)
                    self._z_data = np.roll(self._z_data, -1)
                    
                    self._x_data[-1] = x
                    self._y_data[-1] = y
                    self._z_data[-1] = z
                    
                except ValueError:
                    # Skip invalid data
                    pass
        except Exception as e:
            # Handle any read errors silently
            pass
    
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


class Lab1(QDialog):
    def __init__(self, *args):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Accelerometer Data Visualization")
        
        # Setup sensor and data structures
        self.sensor = AccelerometerSensor(buffer_size=100)
        self.max_x = 10
        self.samples = np.arange(100)
        self.remaining_time = 0
        
        # Setup timers
        self.setup_timers()
        
        # Configure UI elements
        self.setup_ui_elements()
        
        # Initialize plot
        self.init_plot()
    
    def setup_timers(self):
        # Plot update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        
        # Measurement duration timer
        self.measurement_timer = QTimer()
        self.measurement_timer.setSingleShot(True)
        self.measurement_timer.timeout.connect(self.stop_measurement)
        
        # Timer display update
        self.update_timer = QTimer()
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self.update_timer_display)
    
    def setup_ui_elements(self):
        # Configure button
        self.ui.pushButton.setText("Start")
        self.ui.pushButton.clicked.connect(self.toggle_acquisition)
        self.ui.interval.valueChanged.connect(self.update_timer_interval)
        self.ui.maxxaxis.valueChanged.connect(self.update_max_xaxis)
        
        # Configure interval spinner
        self.ui.interval.setRange(0, 300)
        
        # Connect save button
        self.ui.saveButton.clicked.connect(self.save_to_csv)

    def init_plot(self):
        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.axes.set_title('Accelerometer Data')
        self.ui.MplWidget.canvas.axes.set_xlabel('Sample')
        self.ui.MplWidget.canvas.axes.set_ylabel('Acceleration (g)')
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)
        self.ui.MplWidget.canvas.axes.set_ylim(-2, 2)
        self.ui.MplWidget.canvas.axes.grid(True)
        self.x_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'r-', label='X-axis', linewidth=1)
        self.y_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'g-', label='Y-axis', linewidth=1)
        self.z_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'b-', label='Z-axis', linewidth=1)
        self.ui.MplWidget.canvas.axes.legend(loc='upper right')
        self.ui.MplWidget.canvas.draw()
        self.ui.label_timer.setText("Status: Not Connected")
        self.update_plot()
    
    def toggle_acquisition(self):
        if self.sensor.connected:
            self.stop_measurement()
        else:
            if self.sensor.connect(PORT):
                self.ui.label_timer.setText(f"Status: Connected to {PORT}")
                self.timer.start()
                
                self.remaining_time = self.ui.mtime.value()
                if self.remaining_time > 0:
                    self.ui.label_timer.setText(f"Measuring: {self.remaining_time} seconds remaining")
                    self.measurement_timer.start(self.remaining_time * 1000)
                    self.update_timer.start()
                    
                self.ui.pushButton.setText("Stop")
                self.ui.pushButton.setStyleSheet("background-color: red;")
                self.ui.interval.setEnabled(False)
                self.ui.mtime.setEnabled(False)
                self.ui.saveButton.setEnabled(True)
            else:
                QMessageBox.critical(self, "Error", f"Failed to connect to {PORT}")
                
    def update_plot(self):
        """Update the plot with new sensor data"""
        if not self.sensor.connected:
            return
        
        # Read data from the sensor
        self.sensor._read_data()
        
        # Get data directly from the sensor
        x_data = self.sensor.x_data
        y_data = self.sensor.y_data
        z_data = self.sensor.z_data
        
        # Update plot lines with sensor data
        self.x_line.set_data(self.samples, x_data)
        self.y_line.set_data(self.samples, y_data)
        self.z_line.set_data(self.samples, z_data)
        
        # Update statistics
        self.update_statistics()
        
        # Redraw canvas
        self.ui.MplWidget.canvas.draw_idle()
        
        # Update current values display if not in measurement mode
        if not self.measurement_timer.isActive():
            x, y, z = self.sensor.latest_values
            self.ui.label_timer.setText(f"X: {x:.4f} g, Y: {y:.4f} g, Z: {z:.4f} g")
    
    def update_timer_display(self):
        """Update the timer display each second"""
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.ui.label_timer.setText(f"Measuring: {self.remaining_time} seconds remaining")
        else:
            self.update_timer.stop()

    def update_timer_interval(self):
        interval_ms = self.ui.interval.value() * 1000
        self.timer.setInterval(interval_ms)
        
    def update_max_xaxis(self):
        self.max_x = max(1, self.ui.maxxaxis.value())
        self.samples = np.arange(self.max_x)
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)
    
    def stop_measurement(self):
        """Stop the measurement and reset UI"""
        self.timer.stop()
        self.measurement_timer.stop()
        self.update_timer.stop()
        
        if self.sensor.connected:
            self.sensor.disconnect()
        
        self.ui.pushButton.setText("Connect")
        self.ui.pushButton.setStyleSheet("")
        self.ui.label_timer.setText("Status: Disconnected")
        self.ui.interval.setEnabled(True)
    
    def save_to_csv(self):
        """Save current sensor data to a CSV file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Data to CSV", 
            os.path.expanduser("~/Documents/accelerometer_data.csv"),
            "CSV Files (*.csv);;All Files (*)")
        
        if filename:
            # Save data to CSV
            success = self.sensor.save_to_csv(filename)
            
            # Show result message
            if success:
                QMessageBox.information(self, "Success", f"Data saved to {filename}")
                self.ui.label_timer.setText("Status: Connected")
            else:
                QMessageBox.warning(self, "Error", f"Failed to save data to {filename}")
                self.ui.label_timer.setText("Status: Error saving data")
    

    # Update the statistics display directly
    def update_statistics(self):
        if not self.sensor.connected:
            return
            
        # Calculate statistics
        x_mean, y_mean, z_mean = self.sensor.mean_values
        x_std, y_std, z_std = self.sensor.std_values
        
        # Update labels
        labels = [
            (self.ui.meanXLabel, x_mean),
            (self.ui.meanYLabel, y_mean),
            (self.ui.meanZLabel, z_mean),
            (self.ui.stdXLabel, x_std),
            (self.ui.stdYLabel, y_std),
            (self.ui.stdZLabel, z_std)
        ]
        
        for label, value in labels:
            label.setText(f"X: {value:.4f}" if "X:" in label.text() else
                         f"Y: {value:.4f}" if "Y:" in label.text() else
                         f"Z: {value:.4f}")

    def closeEvent(self, event):
        """Handle window close event"""
        if self.sensor.connected:
            self.sensor.disconnect()
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = Lab1()
    form.show()
    sys.exit(app.exec_())