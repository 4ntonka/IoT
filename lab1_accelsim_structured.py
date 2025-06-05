
#!/usr/bin/env python3
"""
Simulated Accelerometer Data Visualization
Exact dezelfde structuur als lab1_accel.py, maar gebruikt random data.
"""

import sys
import os
import time
import csv
import threading
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
import numpy as np
import math
import random
import matplotlib
matplotlib.use("Qt5Agg")

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer
from lab1_ui import Ui_Dialog


class SimulatedSensor:
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

    def start_reading(self):
        # Geen hardware connectie nodig in simulatie
        return True

    def stop_reading(self):
        pass

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

        self._x_latest, self._y_latest, self._z_latest = new_x, new_y, new_z

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


class PlotUpdateWorker(QThread):
    update_finished = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)
    stats_finished = pyqtSignal(tuple, tuple)

    def __init__(self, sensor):
        super().__init__()
        self.sensor = sensor
        self.running = True

    def run(self):
        while self.running:
            self.sensor.generate_data()
            x_data = self.sensor.x_data.copy()
            y_data = self.sensor.y_data.copy()
            z_data = self.sensor.z_data.copy()
            mean_values = self.sensor.mean_values
            std_values = self.sensor.std_values

            self.update_finished.emit(x_data, y_data, z_data)
            self.stats_finished.emit(mean_values, std_values)
            time.sleep(0.1)

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
        self.plot_worker = None
        self.csv_worker = None

        self.setup_timers()
        self.setup_ui_elements()
        self.init_plot()

    def setup_timers(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

    def setup_ui_elements(self):
        self.ui.pushButton.setText("Start")
        self.ui.pushButton.clicked.connect(self.toggle_acquisition)
        self.ui.saveButton.clicked.connect(self.save_to_csv)
        self.ui.interval.valueChanged.connect(self.update_timer_interval)
        self.ui.maxxaxis.valueChanged.connect(self.update_max_xaxis)
        self.update_timer_interval()

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

    def toggle_acquisition(self):
        if self.plot_worker and self.plot_worker.isRunning():
            self.stop_acquisition()
        else:
            self.start_acquisition()

    def start_acquisition(self):
        self.plot_worker = PlotUpdateWorker(self.sensor)
        self.plot_worker.update_finished.connect(self.update_plot)
        self.plot_worker.stats_finished.connect(self.update_stats)
        self.plot_worker.start()
        self.ui.pushButton.setText("Stop")
        self.ui.pushButton.setStyleSheet("background-color: red;")

    def stop_acquisition(self):
        if self.plot_worker:
            self.plot_worker.stop()
            self.plot_worker.wait()
        self.ui.pushButton.setText("Start")
        self.ui.pushButton.setStyleSheet("")

    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray)
    def update_plot(self, x_data, y_data, z_data):
        samples = np.arange(self.max_x)
        self.x_line.set_data(samples, x_data[-self.max_x:])
        self.y_line.set_data(samples, y_data[-self.max_x:])
        self.z_line.set_data(samples, z_data[-self.max_x:])
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)
        self.ui.MplWidget.canvas.draw()

    @pyqtSlot(tuple, tuple)
    def update_stats(self, mean, std):
        x_mean, y_mean, z_mean = mean
        x_std, y_std, z_std = std
        self.ui.meanXLabel.setText(f"X: {x_mean:.4f}")
        self.ui.meanYLabel.setText(f"Y: {y_mean:.4f}")
        self.ui.meanZLabel.setText(f"Z: {z_mean:.4f}")
        self.ui.stdXLabel.setText(f"X: {x_std:.4f}")
        self.ui.stdYLabel.setText(f"Y: {y_std:.4f}")
        self.ui.stdZLabel.setText(f"Z: {z_std:.4f}")

    def update_timer_interval(self):
        interval_ms = self.ui.interval.value() * 1000
        self.timer.setInterval(interval_ms)

    def update_max_xaxis(self):
        self.max_x = self.ui.maxxaxis.value()
        self.samples = np.arange(self.max_x)
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)

    def save_to_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Data to CSV", "", "CSV Files (*.csv)")
        if filename:
            self.csv_worker = CsvSaveWorker(self.sensor, filename)
            self.csv_worker.save_finished.connect(self.on_csv_save_finished)
            self.csv_worker.start()

    @pyqtSlot(bool, str)
    def on_csv_save_finished(self, success, filename):
        if success:
            QMessageBox.information(self, "Success", f"Data saved to {filename}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to save data to {filename}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = Lab1()
    form.show()
    sys.exit(app.exec_())
