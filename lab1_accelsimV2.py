#!/usr/bin/env python3
"""
Simulated Accelerometer Data Visualization with working Interval, Max X, Measure Time and Multithreading.
Structure and function names remain as in the original lab1_accel.py, only their contents have been adapted for simulation.
"""

import sys
import os
import time
import csv
import threading
import numpy as np
import matplotlib.pyplot as plt
import math
import random
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog
from lab1_ui import Ui_Dialog

class SimulatedSensor:
    def __init__(self, buffer_size=100):
        self._buffer_size = buffer_size
        self._x_data = np.zeros(buffer_size)
        self._y_data = np.zeros(buffer_size)
        self._z_data = np.zeros(buffer_size)

    def generate_data(self):
        t = time.time()
        new_x = math.sin(t) + random.uniform(-0.1, 0.1)
        new_y = math.cos(t) + random.uniform(-0.1, 0.1)
        new_z = math.sin(t + 1) + random.uniform(-0.1, 0.1)

        self._x_data = np.roll(self._x_data, -1)
        self._y_data = np.roll(self._y_data, -1)
        self._z_data = np.roll(self._z_data, -1)

        self._x_data[-1] = new_x
        self._y_data[-1] = new_y
        self._z_data[-1] = new_z

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
        return (self._x_data[-1], self._y_data[-1], self._z_data[-1])

    @property
    def mean_values(self):
        return (np.mean(self._x_data), np.mean(self._y_data), np.mean(self._z_data))

    @property
    def std_values(self):
        return (np.std(self._x_data), np.std(self._y_data), np.std(self._z_data))

    def save_to_csv(self, filename):
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Sample', 'X', 'Y', 'Z'])
                for i in range(len(self._x_data)):
                    # afronden op 3 decimalen:
                    row = [
                        i,
                        f"{self._x_data[i]:.3f}",
                        f"{self._y_data[i]:.3f}",
                        f"{self._z_data[i]:.3f}"
                    ]
                    writer.writerow(row)
            return True
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False


# Multi-threading for updating plot and statistics
class PlotUpdateWorker(QThread):
    update_data = pyqtSignal(np.ndarray, np.ndarray, np.ndarray, tuple, tuple)

    def __init__(self, sensor, interval_ms):
        super().__init__()
        self.sensor = sensor
        self.interval_ms = interval_ms
        self.running = True

    def run(self):
        while self.running:
            self.sensor.generate_data()
            x_data = self.sensor.x_data[-self.sensor._buffer_size:]
            y_data = self.sensor.y_data[-self.sensor._buffer_size:]
            z_data = self.sensor.z_data[-self.sensor._buffer_size:]
            mean = self.sensor.mean_values
            std = self.sensor.std_values
            self.update_data.emit(x_data, y_data, z_data, mean, std)
            sleep_time = self.interval_ms if self.interval_ms > 0 else 100
            self.msleep(sleep_time)

    def stop(self):
        self.running = False


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
    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Simulated Accelerometer Data Visualization")

        self.sensor = SimulatedSensor(buffer_size=100)
        self.max_x = 10
        self.samples = np.arange(100)
        self.remaining_time = 0

        self.timer = QTimer()

        self.measurement_timer = QTimer()
        self.measurement_timer.setSingleShot(True)
        self.measurement_timer.timeout.connect(self.stop_measurement)

        self.ui.pushButton.setText("Start")
        self.ui.pushButton.clicked.connect(self.toggle_measurement)
        self.ui.saveButton.clicked.connect(self.save_to_csv)
        self.ui.interval.valueChanged.connect(self.update_timer_interval)
        self.ui.maxxaxis.valueChanged.connect(self.update_max_xaxis)
        self.update_timer_interval()
        self.init_plot()

    def init_plot(self):
        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.axes.set_title("Simulated Accelerometer Data")
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)
        self.ui.MplWidget.canvas.axes.set_ylim(-2, 2)
        self.ui.MplWidget.canvas.axes.grid(True)
        self.x_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'r-', label='X-axis')
        self.y_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'g-', label='Y-axis')
        self.z_line, = self.ui.MplWidget.canvas.axes.plot([], [], 'b-', label='Z-axis')
        self.ui.MplWidget.canvas.axes.legend()
        self.ui.MplWidget.canvas.draw()
        self.ui.label_timer.setText("Status: Not Measuring")

    def toggle_measurement(self):
        if self.timer.isActive():
            self.stop_measurement()
        else:
            self.start_measurement()

    def start_measurement(self):
        self.sensor._x_data.fill(0)
        self.sensor._y_data.fill(0)
        self.sensor._z_data.fill(0)
        self.plot_worker = PlotUpdateWorker(self.sensor,  self.current_interval_ms)
        self.plot_worker.update_data.connect(self.handle_update)
        self.plot_worker.start()
        self.ui.label_timer.setText("Measuring...")
        self.remaining_time = self.ui.mtime.value()
        self.timer.start(self.ui.interval.value() * 1000)
        self.measurement_timer.start(self.remaining_time * 1000)
        self.ui.pushButton.setText("Stop")
        self.ui.pushButton.setStyleSheet("background-color: red;")
        self.ui.interval.setEnabled(False)
        self.ui.maxxaxis.setEnabled(False)
        self.ui.mtime.setEnabled(False)
        self.ui.saveButton.setEnabled(True)

    def stop_measurement(self):
        if self.plot_worker:
            self.plot_worker.stop()
            self.plot_worker.wait()
        self.timer.stop()
        self.measurement_timer.stop()
        self.ui.pushButton.setText("Start")
        self.ui.pushButton.setStyleSheet("")
        self.ui.label_timer.setText("Status: Not Measuring")
        self.ui.interval.setEnabled(True)
        self.ui.maxxaxis.setEnabled(True)
        self.ui.mtime.setEnabled(True)
        self.ui.saveButton.setEnabled(True)

        # Reset de grafieklijnen (stripchart)
        self.x_line.set_data([], [])
        self.y_line.set_data([], [])
        self.z_line.set_data([], [])

    def update_timer_interval(self):
       self.current_interval_ms = self.ui.interval.value() * 1000

    def update_max_xaxis(self):
        self.max_x = self.ui.maxxaxis.value()
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)

    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray, tuple, tuple)
    def handle_update(self, x_data, y_data, z_data, mean, std):
        samples = np.arange(self.max_x)
        self.x_line.set_data(samples, x_data[-self.max_x:])
        self.y_line.set_data(samples, y_data[-self.max_x:])
        self.z_line.set_data(samples, z_data[-self.max_x:])
        self.ui.MplWidget.canvas.axes.yaxis.set_major_formatter(plt.FuncFormatter(lambda val, _: f"{val:.3f}"))
        self.ui.MplWidget.canvas.draw()
        self.ui.meanXLabel.setText(f"X: {mean[0]:.3f}")
        self.ui.meanYLabel.setText(f"Y: {mean[1]:.3f}")
        self.ui.meanZLabel.setText(f"Z: {mean[2]:.3f}")
        self.ui.stdXLabel.setText(f"X: {std[0]:.3f}")
        self.ui.stdYLabel.setText(f"Y: {std[1]:.3f}")
        self.ui.stdZLabel.setText(f"Z: {std[2]:.3f}")

    def save_to_csv(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Data to CSV", 
            os.path.expanduser("~/Downloads/accelerometer_data.csv"),
            "CSV Files (*.csv);;All Files (*)")
        if filename:
            self.ui.pushButton.setEnabled(False)  # Disable UI elements during save
            self.ui.saveButton.setEnabled(False)
            self.ui.label_timer.setText("Saving data to CSV...")
            self.csv_worker = CsvSaveWorker(self.sensor, filename)
            self.csv_worker.save_finished.connect(self.on_csv_save_finished)
            self.csv_worker.start()

    @pyqtSlot(bool, str)
    def on_csv_save_finished(self, success, filename):
        self.ui.pushButton.setEnabled(True)
        self.ui.saveButton.setEnabled(True)
        self.ui.label_timer.setText("Status: Not Measuring")
        if success:
            QMessageBox.information(self, "Success", f"Data saved to {filename}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to save data to {filename}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = Lab1()
    form.show()
    sys.exit(app.exec_())
