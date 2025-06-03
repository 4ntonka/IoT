#!/usr/bin/env python3
"""
Accelerometer Data Visualization - Simulatieversie

Deze versie genereert willekeurige data voor X, Y en Z.
Handig om de UI en functionaliteit te testen zonder hardware!
"""

import sys
import os
import csv
import random
import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")

from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QTimer
from lab1_ui import Ui_Dialog


class RandomSensor:
    """Simuleert een accelerometer met willekeurige data."""
    
    def __init__(self, buffer_size=100):
        self._buffer_size = buffer_size
        self._x_data = np.zeros(buffer_size)
        self._y_data = np.zeros(buffer_size)
        self._z_data = np.zeros(buffer_size)
        self._x_latest = 0.0
        self._y_latest = 0.0
        self._z_latest = 0.0

    @property
    def x_data(self):
        return self._x_data
    
    @property
    def y_data(self):
        return self._y_data
    
    @property
    def z_data(self):
        return self._z_data
    
    @property
    def latest_values(self):
        return (self._x_latest, self._y_latest, self._z_latest)
    
    @property
    def mean_values(self):
        return (
            np.mean(self._x_data),
            np.mean(self._y_data),
            np.mean(self._z_data)
        )
    
    @property
    def std_values(self):
        return (
            np.std(self._x_data),
            np.std(self._y_data),
            np.std(self._z_data)
        )
    
    def generate_data(self):
        """Genereert willekeurige data en update de arrays."""
        x, y, z = random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)
        self._x_data = np.roll(self._x_data, -1)
        self._y_data = np.roll(self._y_data, -1)
        self._z_data = np.roll(self._z_data, -1)
        self._x_data[-1] = x
        self._y_data[-1] = y
        self._z_data[-1] = z
        self._x_latest, self._y_latest, self._z_latest = x, y, z
    
    def save_to_csv(self, filename):
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Sample', 'X', 'Y', 'Z'])
                data = np.column_stack((
                    np.arange(len(self._x_data)),
                    self._x_data,
                    self._y_data,
                    self._z_data
                ))
                writer.writerows(data)
            return True
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False


class Lab1(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Accelerometer Data Visualization - Simulatie")
        
        self.sensor = RandomSensor(buffer_size=100)
        self.max_x = self.ui.maxxaxis.value()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        
        self.ui.pushButton.setText("Start")
        self.ui.pushButton.clicked.connect(self.toggle_simulation)
        self.ui.interval.valueChanged.connect(self.update_timer_interval)
        self.ui.maxxaxis.valueChanged.connect(self.update_max_xaxis)
        self.ui.saveButton.clicked.connect(self.save_to_csv)
        
        self.update_timer_interval()
        self.init_plot()
    
    def init_plot(self):
        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.axes.set_title("Accelerometer Data (Simulatie)")
        self.ui.MplWidget.canvas.axes.set_xlabel("Sample")
        self.ui.MplWidget.canvas.axes.set_ylabel("Acceleration (g)")
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)
        self.ui.MplWidget.canvas.axes.set_ylim(-2, 2)
        self.ui.MplWidget.canvas.axes.grid(True)
        self.x_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'r-', label='X-axis')
        self.y_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'g-', label='Y-axis')
        self.z_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'b-', label='Z-axis')
        self.ui.MplWidget.canvas.axes.legend(loc='upper right')
        self.ui.MplWidget.canvas.draw()
        self.ui.label_timer.setText("Status: Not Connected (Simulatie)")
    
    def toggle_simulation(self):
        if self.timer.isActive():
            self.timer.stop()
            self.ui.pushButton.setText("Start")
        else:
            self.timer.start()
            self.ui.pushButton.setText("Stop")
    
    def update_plot(self):
        self.sensor.generate_data()
        
        x_data = self.sensor.x_data[-self.max_x:]
        y_data = self.sensor.y_data[-self.max_x:]
        z_data = self.sensor.z_data[-self.max_x:]
        samples = np.arange(len(x_data))
        
        self.x_line.set_data(samples, x_data)
        self.y_line.set_data(samples, y_data)
        self.z_line.set_data(samples, z_data)
        
        self.update_statistics()
        x, y, z = self.sensor.latest_values
        self.ui.label_timer.setText(f"X: {x:.4f} g, Y: {y:.4f} g, Z: {z:.4f} g")
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)
        self.ui.MplWidget.canvas.draw()
    
    def update_timer_interval(self):
        interval_ms = self.ui.interval.value() * 100  # 0.1s per stap
        self.timer.setInterval(interval_ms)
    
    def update_max_xaxis(self):
        self.max_x = self.ui.maxxaxis.value()
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)
    
    def update_statistics(self):
        x_mean, y_mean, z_mean = self.sensor.mean_values
        x_std, y_std, z_std = self.sensor.std_values
        
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
    
    def save_to_csv(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Data to CSV",
            os.path.expanduser("~/Documents/random_accel_data.csv"),
            "CSV Files (*.csv);;All Files (*)")
        if filename and self.sensor.save_to_csv(filename):
            QMessageBox.information(self, "Success", f"Data saved to {filename}")
        elif filename:
            QMessageBox.warning(self, "Error", "Failed to save data to file.")
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = Lab1()
    form.show()
    sys.exit(app.exec_())
