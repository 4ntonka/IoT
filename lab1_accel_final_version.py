#!/usr/bin/env python3
"""
Final version: Accelerometer Data Visualization with real-time updates, multithreading and UI features.
Based on accelsimV2.py, adapted for real Arduino accelerometer data.
"""

import sys
import os
import time
import csv
import numpy as np
import serial
import serial.tools.list_ports
import threading
import math
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog
from lab1_ui import Ui_Dialog

PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

class AccelerometerSensor:
    def __init__(self, buffer_size=100):
        self._buffer_size = buffer_size
        self._x_data = np.zeros(buffer_size)
        self._y_data = np.zeros(buffer_size)
        self._z_data = np.zeros(buffer_size)
        self._x_latest = 0.0
        self._y_latest = 0.0
        self._z_latest = 0.0
        self._serial = None
        self._connected = False
        self._reading = False
        self._stop_event = threading.Event()
        self._thread = None

    @property
    def connected(self):
        return self._connected and self._serial is not None

    @property
    def reading(self):
        return self._reading

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
        return (np.mean(self._x_data), np.mean(self._y_data), np.mean(self._z_data))

    @property
    def std_values(self):
        return (np.std(self._x_data), np.std(self._y_data), np.std(self._z_data))

    def list_ports(self):
        ports = list(serial.tools.list_ports.comports())
        return [(p.device, p.description) for p in ports]

    def connect(self, port=PORT, baudrate=BAUD_RATE, timeout=1):
        try:
            self._serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)
            self._serial.reset_input_buffer()
            self._connected = True
            return True
        except (serial.SerialException, ValueError) as e:
            print(f"Error connecting to {port}: {e}")
            self._connected = False
            self._serial = None
            return False

    def disconnect(self):
        self.stop_reading()
        if self._serial:
            self._serial.close()
        self._serial = None
        self._connected = False

    def _read_data(self):
        while not self._stop_event.is_set():
            if not self._connected or self._serial is None:
                time.sleep(0.1)
                continue
            try:
                if self._serial.in_waiting > 0:
                    self._process_serial_data()
                time.sleep(0.01)
            except Exception as e:
                print(f"Error reading data: {e}")
                self._connected = False
                break

    def _process_serial_data(self):
        line = self._serial.readline().decode('utf-8').strip()
        parts = line.split(',')
        if len(parts) == 3:
            try:
                x, y, z = map(float, parts)
                self._x_latest, self._y_latest, self._z_latest = x, y, z
                self._x_data = np.roll(self._x_data, -1)
                self._y_data = np.roll(self._y_data, -1)
                self._z_data = np.roll(self._z_data, -1)
                self._x_data[-1] = x
                self._y_data[-1] = y
                self._z_data[-1] = z
            except ValueError:
                pass

    def start_reading(self):
        if not self._connected:
            return False
        self._serial.reset_input_buffer()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._read_data)
        self._thread.daemon = True
        self._thread.start()
        self._reading = True
        return True

    def stop_reading(self):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=1.0)
        self._reading = False

    def save_to_csv(self, filename):
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Sample', 'X', 'Y', 'Z'])
                data = np.column_stack((np.arange(len(self._x_data)), self._x_data, self._y_data, self._z_data))
                writer.writerows(data)
            return True
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False

class PlotUpdateWorker(QThread):
    update_data = pyqtSignal(np.ndarray, np.ndarray, np.ndarray, tuple, tuple)

    def __init__(self, sensor, interval_ms=100):
        super().__init__()
        self.sensor = sensor
        self.interval_ms = interval_ms
        self.running = True

    def run(self):
        self.sensor.start_reading()
        while self.running:
            x_data = self.sensor.x_data.copy()
            y_data = self.sensor.y_data.copy()
            z_data = self.sensor.z_data.copy()
            mean = self.sensor.mean_values
            std = self.sensor.std_values
            self.update_data.emit(x_data, y_data, z_data, mean, std)
            self.msleep(100)

    def stop(self):
        self.running = False
        self.sensor.stop_reading()

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
        self.setWindowTitle("Accelerometer Data Visualization - Real Sensor")

        self.sensor = AccelerometerSensor(buffer_size=100)
        self.max_x = 10
        self.plot_worker = None
        self.csv_worker = None

        self.measurement_timer = QTimer()
        self.measurement_timer.setSingleShot(True)
        self.measurement_timer.timeout.connect(self.stop_measurement)

        self.ui.pushButton.clicked.connect(self.toggle_measurement)
        self.ui.saveButton.clicked.connect(self.save_to_csv)
        self.ui.interval.valueChanged.connect(self.update_timer_interval)
        self.ui.maxxaxis.valueChanged.connect(self.update_max_xaxis)
        self.init_plot()

    def init_plot(self):
        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.axes.set_title("Accelerometer Data")
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
        if self.plot_worker and self.plot_worker.isRunning():
            self.stop_measurement()
        else:
            self.start_measurement()

    def start_measurement(self):
        if not self.sensor.connected:
            QMessageBox.critical(self, "Error", f"Failed to connect to {PORT}")
            return
        self.ui.label_timer.setText("Measuring...")
        interval_ms = self.ui.interval.value() * 1000
        self.plot_worker = PlotUpdateWorker(self.sensor, interval_ms)
        self.plot_worker.update_data.connect(self.handle_update)
        self.plot_worker.start()
        self.measurement_timer.start(self.ui.mtime.value() * 1000)
        self.ui.pushButton.setText("Stop")
        self.ui.pushButton.setStyleSheet("background-color: red;")

    def stop_measurement(self):
        if self.plot_worker:
            self.plot_worker.stop()
            self.plot_worker.wait()
        self.ui.pushButton.setText("Start")
        self.ui.pushButton.setStyleSheet("")
        self.ui.label_timer.setText("Measurement stopped & plot reset")
        self.ui.interval.setEnabled(True)
        self.ui.maxxaxis.setEnabled(True)
        self.ui.mtime.setEnabled(True)
        # Plot reset
        self.sensor._x_data.fill(0)
        self.sensor._y_data.fill(0)
        self.sensor._z_data.fill(0)
        self.x_line.set_data([], [])
        self.y_line.set_data([], [])
        self.z_line.set_data([], [])
        self.ui.MplWidget.canvas.draw()

    def update_timer_interval(self):
        pass  # Interval wordt direct aan de worker doorgegeven bij start

    def update_max_xaxis(self):
        self.max_x = self.ui.maxxaxis.value()
        self.ui.MplWidget.canvas.axes.set_xlim(0, self.max_x)

    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray, tuple, tuple)
    def handle_update(self, x_data, y_data, z_data, mean, std):
        samples = np.arange(len(x_data[-self.max_x:]))
        self.x_line.set_data(samples, x_data[-self.max_x:])
        self.y_line.set_data(samples, y_data[-self.max_x:])
        self.z_line.set_data(samples, z_data[-self.max_x:])
        self.ui.MplWidget.canvas.draw()
        self.ui.meanXLabel.setText(f"X: {mean[0]:.4f}")
        self.ui.meanYLabel.setText(f"Y: {mean[1]:.4f}")
        self.ui.meanZLabel.setText(f"Z: {mean[2]:.4f}")
        self.ui.stdXLabel.setText(f"X: {std[0]:.4f}")
        self.ui.stdYLabel.setText(f"Y: {std[1]:.4f}")
        self.ui.stdZLabel.setText(f"Z: {std[2]:.4f}")

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