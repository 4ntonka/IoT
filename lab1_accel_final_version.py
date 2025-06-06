#!/usr/bin/env python3
"""
Accelerometer Data Visualization with real-time updates, multithreading and UI features.
"""

import sys
import os
import time
import csv
import numpy as np
import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
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

class PlotUpdateWorker(QThread):
    update_data = pyqtSignal(np.ndarray, np.ndarray, np.ndarray, tuple, tuple)

    def __init__(self, sensor, interval_ms):
        super().__init__()
        self.sensor = sensor
        self.interval_ms = interval_ms
        self.running = True

    def run(self):
        while self.running:
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
        self.plot_worker = None
        self.csv_worker = None
        self.timer = QTimer()
        self.measurement_timer = QTimer()
        self.measurement_timer.setSingleShot(True)
        self.measurement_timer.timeout.connect(self.stop_measurement)
        self.total_samples = 0
        self.current_x_samples = []

        self.ui.pushButton.clicked.connect(self.toggle_measurement)
        self.ui.saveButton.clicked.connect(self.save_to_csv)
        self.ui.interval.valueChanged.connect(self.update_timer_interval)
        self.update_timer_interval()
        self.init_plot()

    def init_plot(self):
        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.axes.set_title("Accelerometer Data")
        self.ui.MplWidget.canvas.axes.set_xlim(0, 10)
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
            if not self.sensor.connect(PORT):
                QMessageBox.critical(self, "Error", f"Failed to connect to {PORT}")
                return
        else:
            self.ui.label_timer.setText(f"Status: Connected to {PORT}")
            self.sensor.start_reading()
        if not hasattr(self, "sensor_initialized") or not self.sensor_initialized:
            self.sensor_initialized = True
            time.sleep(1)
            self.sensor.stop_reading()
            self.sensor.start_reading()
        self.current_x_samples = []  # Start opnieuw bij 0 voor nieuwe meting
        self.total_samples = 0  # Reset de sample teller
        self.plot_worker = PlotUpdateWorker(self.sensor, self.current_interval_ms)
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

        # **Belangrijk: reset plot_x**
        self.plot_x = []

    def update_timer_interval(self):
        self.current_interval_ms = self.ui.interval.value() * 1000

    @pyqtSlot(np.ndarray, np.ndarray, np.ndarray, tuple, tuple)
    def handle_update(self, x_data, y_data, z_data, mean, std):

        self.total_samples += 1
        if not hasattr(self, "plot_x"):
            self.plot_x = []

        self.plot_x.append(self.total_samples - 1)

        # Rolling window: houd plot_x even lang als buffer
        if len(self.plot_x) > self.sensor._buffer_size:
            self.plot_x = self.plot_x[-self.sensor._buffer_size:]

        # Bepaal hoeveel punten er in plot_x staan
        num_points = len(self.plot_x)

        # Pak de laatste num_points samples uit y-data
        self.x_line.set_data(self.plot_x, x_data[-num_points:])
        self.y_line.set_data(self.plot_x, y_data[-num_points:])
        self.z_line.set_data(self.plot_x, z_data[-num_points:])

        self.ui.MplWidget.canvas.axes.set_xlim(self.plot_x[0], self.plot_x[-1])

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
        if success:
            QMessageBox.information(self, "Success", f"Data saved to {filename}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to save data to {filename}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = Lab1()
    form.show()
    sys.exit(app.exec_())