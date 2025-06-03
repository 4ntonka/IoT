#!/usr/bin/env python3
import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")

from PyQt5.QtWidgets import (QApplication, QDialog, QMessageBox, QPushButton, 
                             QLabel, QGroupBox, QVBoxLayout, QFileDialog, 
                             QSpinBox, QGridLayout)
from PyQt5.QtCore import QTimer, Qt
from lab1_ui import Ui_Dialog
from accelerometer_sensor import AccelerometerSensor

PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

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
        
        # Configure interval spinner
        self.ui.interval.setRange(1, 300)
        self.ui.interval.setValue(60)
        self.ui.interval.setSuffix(" sec")
        self.ui.interval_label.setText("Measure time (s):")
        
        # Add save button
        self.ui.saveButton = QPushButton("Save to CSV", self)
        self.ui.saveButton.setGeometry(10, 205, 100, 28)
        self.ui.saveButton.clicked.connect(self.save_to_csv)
        self.ui.saveButton.setEnabled(False)
        
        # Add statistics group
        self.setup_statistics_ui()

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
    
    def update_plot(self):
        """Update the plot with new sensor data"""
        if not self.sensor.connected or not self.sensor.reading:
            return
            
        # Update plot lines with sensor data
        self.x_line.set_data(self.samples, self.sensor.x_data)
        self.y_line.set_data(self.samples, self.sensor.y_data)
        self.z_line.set_data(self.samples, self.sensor.z_data)
        
        # Update current values display if not in measurement mode
        if not self.measurement_timer.isActive():
            x, y, z = self.sensor.latest_values
            self.ui.label_timer.setText(f"X: {x:.4f} g, Y: {y:.4f} g, Z: {z:.4f} g")
        
        # Update statistics and redraw
        self.update_statistics()
        self.ui.MplWidget.canvas.draw()
    
    def update_timer_display(self):
        """Update the timer display each second"""
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.ui.label_timer.setText(f"Measuring: {self.remaining_time} seconds remaining")
        else:
            self.update_timer.stop()
    
    def stop_measurement(self):
        """Stop the measurement and reset UI"""
        self.timer.stop()
        self.measurement_timer.stop()
        self.update_timer.stop()
        
        if self.sensor.connected:
            self.sensor.stop_reading()
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
        
        if filename and self.sensor.save_to_csv(filename):
            QMessageBox.information(self, "Success", f"Data saved to {filename}")
        elif filename:
            QMessageBox.warning(self, "Error", f"Failed to save data to {filename}")
    
    def setup_statistics_ui(self):
        # Create statistics panel
        self.ui.statsGroupBox = QGroupBox("Statistics", self)
        self.ui.statsGroupBox.setGeometry(10, 240, 130, 150)
        layout = QVBoxLayout(self.ui.statsGroupBox)
        
        # Create labels for statistics
        self.ui.meanLabel = QLabel("Mean:")
        self.ui.meanXLabel = QLabel("X: 0.0000")
        self.ui.meanYLabel = QLabel("Y: 0.0000")
        self.ui.meanZLabel = QLabel("Z: 0.0000")
        
        self.ui.stdLabel = QLabel("Std Dev:")
        self.ui.stdXLabel = QLabel("X: 0.0000")
        self.ui.stdYLabel = QLabel("Y: 0.0000")
        self.ui.stdZLabel = QLabel("Z: 0.0000")
        
        # Add labels to layout
        for label in [self.ui.meanLabel, self.ui.meanXLabel, self.ui.meanYLabel, 
                     self.ui.meanZLabel, self.ui.stdLabel, self.ui.stdXLabel, 
                     self.ui.stdYLabel, self.ui.stdZLabel]:
            layout.addWidget(label)
            
    def update_statistics(self):
        """Update the statistics display"""
        if not self.sensor.connected:
            return
        
        # Update mean values
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