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
import threading
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot # Import QThread and signals/slots
import numpy as np
import serial
import serial.tools.list_ports
import matplotlib
matplotlib.use("Qt5Agg")

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer
from lab1_ui import Ui_Dialog

PORT = '/dev/ttyACM0'
BAUD_RATE = 9600


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


# Multi-threading for updating plot and statistics
class PlotUpdateWorker(QThread):
    update_finished = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    stats_finished = pyqtSignal(tuple, tuple)
    
    def __init__(self, sensor):
        super().__init__()
        self.sensor = sensor
        self.running = True
    
    def run(self):
        while self.running and self.sensor.connected and self.sensor.reading:
            # Get data from sensor
            x_data = self.sensor.x_data.copy()
            y_data = self.sensor.y_data.copy()
            z_data = self.sensor.z_data.copy()
            
            # Calculate statistics
            mean_values = self.sensor.mean_values
            std_values = self.sensor.std_values
            
            # Emit signals with data
            self.update_finished.emit(x_data, y_data, z_data)
            self.stats_finished.emit(mean_values, std_values)
            
            # Sleep to reduce CPU usage
            time.sleep(0.1)
    
    def stop(self):
        self.running = False


# Multi-threading for saving CSV files
class CsvSaveWorker(QThread):
    save_finished = pyqtSignal(bool, str)
    
    def __init__(self, sensor, filename):
        super().__init__()
        self.sensor = sensor
        self.filename = filename
    
    def run(self):
        success = self.sensor.save_to_csv(self.filename)
        self.save_finished.emit(success, self.filename)


class Lab1(QDialog):
    def __init__(self, *args):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Accelerometer Data Visualization")
        
        # Setup sensor and data structures
        self.sensor = AccelerometerSensor(buffer_size=100)
        self.samples = np.arange(100)
        self.remaining_time = 0
        
        # Initialize worker threads
        self.plot_worker = None
        self.csv_worker = None
        
        # Setup timers
        self.setup_timers()
        
        # Configure UI elements
        self.setup_ui_elements()
        
        # Initialize plot
        self.init_plot()
    
    def setup_timers(self):
        # Plot update timer
        self.timer = QTimer()
        self.timer.setInterval(100)
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
        self.ui.pushButton.setText("Connect")
        self.ui.pushButton.clicked.connect(self.toggle_acquisition)
        self.ui.interval.valueChanged.connect(self.update_timer_interval)
        self.ui.maxxaxis.valueChanged.connect(self.update_max_xaxis)
        
        # Configure interval spinner
        self.ui.interval.setRange(1, 300)
        self.ui.interval.setValue(60)
        self.ui.interval.setSuffix(" sec")
        self.ui.interval_label.setText("Measure time (s):")
        
        # Connect save button
        self.ui.saveButton.clicked.connect(self.save_to_csv)

    def init_plot(self):
        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.axes.set_title('Accelerometer Data')
        self.ui.MplWidget.canvas.axes.set_xlabel('Sample')
        self.ui.MplWidget.canvas.axes.set_ylabel('Acceleration (g)')
        self.ui.MplWidget.canvas.axes.set_xlim(0, 100)
        self.ui.MplWidget.canvas.axes.set_ylim(-2, 2)
        self.ui.MplWidget.canvas.axes.grid(True)
        self.x_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'r-', label='X-axis', linewidth=1)
        self.y_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'g-', label='Y-axis', linewidth=1)
        self.z_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'b-', label='Z-axis', linewidth=1)
        self.ui.MplWidget.canvas.axes.legend(loc='upper right')
        self.ui.MplWidget.canvas.draw()
        self.ui.label_timer.setText("Status: Not Connected")
    
    def toggle_acquisition(self):
        if self.sensor.connected:
            self.stop_measurement()
        else:
            if self.sensor.connect(PORT):
                self.ui.label_timer.setText(f"Status: Connected to {PORT}")
                self.sensor.start_reading()   
                
                # Start worker thread for plot updates
                self.start_worker_thread()
                
                # Start UI update timer (lightweight)
                self.timer.start()
                
                self.remaining_time = self.ui.interval.value()
                if self.remaining_time > 0:
                    self.ui.label_timer.setText(f"Measuring: {self.remaining_time} seconds remaining")
                    self.measurement_timer.start(self.remaining_time * 1000)
                    self.update_timer.start()
                    
                self.ui.pushButton.setText("Stop")
                self.ui.pushButton.setStyleSheet("background-color: red;")
                self.ui.interval.setEnabled(False)
                self.ui.saveButton.setEnabled(True)
            else:
                QMessageBox.critical(self, "Error", f"Failed to connect to {PORT}")
                
    def start_worker_thread(self):
        # Create and start the worker thread for plot updates
        if self.plot_worker is None or not self.plot_worker.isRunning():
            self.plot_worker = PlotUpdateWorker(self.sensor)
            self.plot_worker.update_finished.connect(self.update_plot_data)
            self.plot_worker.stats_finished.connect(self.update_stats_data)
            self.plot_worker.start()
    
    def update_plot(self):
        """Lightweight method to trigger UI updates from the main thread timer"""
        if not self.sensor.connected or not self.sensor.reading:
            return
            
        # Update current values display if not in measurement mode
        if not self.measurement_timer.isActive():
            x, y, z = self.sensor.latest_values
            self.ui.label_timer.setText(f"X: {x:.4f} g, Y: {y:.4f} g, Z: {z:.4f} g")
    
    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def update_plot_data(self, x_data, y_data, z_data):
        """Update plot with data from worker thread"""
        # Update plot lines with sensor data
        self.x_line.set_data(self.samples, x_data)
        self.y_line.set_data(self.samples, y_data)
        self.z_line.set_data(self.samples, z_data)
        
        # Redraw canvas - this is the UI operation that needs to be in main thread
        self.ui.MplWidget.canvas.draw()
    
    def update_timer_display(self):
        """Update the timer display each second"""
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.ui.label_timer.setText(f"Measuring: {self.remaining_time} seconds remaining")
        else:
            self.update_timer.stop()

    def update_timer_interval(self):
        self.update_interval = self.ui.interval.value()
        self.timer.setInterval(self.update_interval)
        
    def update_max_xaxis(self):
        self.max_x = self.ui.maxxaxis.value()
        self.samples = np.arange(self.max_x)
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)
    
    def stop_measurement(self):
        """Stop the measurement and reset UI"""
        self.timer.stop()
        self.measurement_timer.stop()
        self.update_timer.stop()
        
        # Stop worker thread
        if self.plot_worker is not None and self.plot_worker.isRunning():
            self.plot_worker.stop()
            self.plot_worker.wait(1000)  # Wait up to 1 second for the thread to finish
            if self.plot_worker.isRunning():
                self.plot_worker.terminate()  # Force termination if needed
        
        if self.sensor.connected:
            self.sensor.stop_reading()
            self.sensor.disconnect()
        
        self.ui.pushButton.setText("Connect")
        self.ui.pushButton.setStyleSheet("")
        self.ui.label_timer.setText("Status: Disconnected")
        self.ui.interval.setEnabled(True)
    
    def save_to_csv(self):
        """Save current sensor data to a CSV file using a worker thread"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Data to CSV", 
            os.path.expanduser("~/Documents/accelerometer_data.csv"),
            "CSV Files (*.csv);;All Files (*)")
        
        if filename:
            # Create progress dialog
            self.ui.pushButton.setEnabled(False)  # Disable UI elements during save
            self.ui.saveButton.setEnabled(False)
            self.ui.label_timer.setText("Saving data to CSV...")
            
            # Create and start worker thread
            self.csv_worker = CsvSaveWorker(self.sensor, filename)
            self.csv_worker.save_finished.connect(self.on_csv_save_finished)
            self.csv_worker.start()
    
    @pyqtSlot(bool, str)
    def on_csv_save_finished(self, success, filename):
        """Handle CSV save completion"""
        # Re-enable UI elements
        self.ui.pushButton.setEnabled(True)
        self.ui.saveButton.setEnabled(True)
        
        # Show result message
        if success:
            QMessageBox.information(self, "Success", f"Data saved to {filename}")
            self.ui.label_timer.setText("Status: Connected")
        else:
            QMessageBox.warning(self, "Error", f"Failed to save data to {filename}")
            self.ui.label_timer.setText("Status: Error saving data")
    

            
    @pyqtSlot(tuple, tuple)
    def update_stats_data(self, mean_values, std_values):
        """Update statistics display with data from worker thread"""
        if not self.sensor.connected:
            return
        
        # Unpack values
        x_mean, y_mean, z_mean = mean_values
        x_std, y_std, z_std = std_values
        
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
        # Stop any running worker threads
        if self.plot_worker is not None and self.plot_worker.isRunning():
            self.plot_worker.stop()
            self.plot_worker.wait(1000)  # Wait up to 1 second for the thread to finish
        
        if self.csv_worker is not None and self.csv_worker.isRunning():
            self.csv_worker.wait(1000)  # Wait for CSV save to complete
        
        if self.sensor.connected:
            self.sensor.disconnect()
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = Lab1()
    form.show()
    sys.exit(app.exec_())