#!/usr/bin/env python3
import serial


import sys
import numpy as np
from PyQt5.QtWidgets import *
from lab1_ui import *
import matplotlib
import serial.tools.list_ports

matplotlib.use("Qt5Agg")
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtCore import QTimer
from accelerometer_sensor import AccelerometerSensor

PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

class Lab1(QDialog):
    def __init__(self, *args):
        QDialog.__init__(self)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Accelerometer Data Visualization")
        
        self.sensor = AccelerometerSensor(buffer_size=100)
        self.samples = np.arange(100)  
        self.ui.pushButton.setText("Connect")
        self.ui.pushButton.clicked.connect(self.toggle_acquisition)
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_plot)
        self.init_plot()

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
            self.timer.stop()
            self.sensor.stop_reading()
            self.sensor.disconnect()
            self.ui.pushButton.setText("Connect")
            self.ui.label_timer.setText("Status: Disconnected")
        else:
            ports = self.sensor.list_ports()
            if not ports:
                QMessageBox.warning(self, "Error", "No serial ports found")
                return
            
            if self.sensor.connect(PORT):
                self.ui.label_timer.setText(f"Status: Connected to {PORT}")
                self.sensor.start_reading()   
                self.timer.start()
                self.ui.pushButton.setText("Disconnect")
            else:
                QMessageBox.critical(self, "Error", f"Failed to connect to {PORT}")
    
    def update_plot(self):
        if not self.sensor.connected or not self.sensor.reading:
            return
        x_data = self.sensor.x_data
        y_data = self.sensor.y_data
        z_data = self.sensor.z_data
        self.x_line.set_data(self.samples, x_data)
        self.y_line.set_data(self.samples, y_data)
        self.z_line.set_data(self.samples, z_data)
        x, y, z = self.sensor.latest_values
        self.ui.label_timer.setText(f"X: {x:.4f} g, Y: {y:.4f} g, Z: {z:.4f} g")
        self.ui.MplWidget.canvas.draw()
    
    def closeEvent(self, event):
        if self.sensor.connected:
            self.sensor.disconnect()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = Lab1()
    form.show()
    sys.exit(app.exec_())