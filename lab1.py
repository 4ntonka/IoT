import sys
import random
from PyQt5.QtWidgets import *
from lab1_ui import *
import matplotlib

matplotlib.use("Qt5Agg")
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


class Lab1(QDialog):
    def __init__(self, *args):
        QDialog.__init__(self)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("arduino_sensors")
        self.remaining_time = 10

        self.x = list(range(1, 11)) 
        self.y = [random.uniform(0, 1) for _ in self.x] 

        self.ui.pushButton.clicked.connect(self.toggle_timer)
        self.timer = QTimer()
        self.timer.setInterval(500)  # 500 ms = 0,5 seconden
        self.timer.timeout.connect(self.mybuttonfunction)
        # Display initial plot when application starts
        self.mybuttonfunction()

    def mybuttonfunction(self):
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.ui.label_timer.setText(f"{self.remaining_time} seconds")
        if self.remaining_time == 0:
            self.timer.stop()
        # Update plot (optioneel)
        new_value = random.uniform(0, 1)
        self.y.append(new_value)
        if len(self.y) > 10:
            self.y.pop(0)

        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.axes.plot(self.x, self.y, 'r', linewidth=0.5)
        self.ui.MplWidget.canvas.draw()

    def update_random(self):
        self.y = [random.uniform(0, 1) for _ in self.x] 

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self.ui.pushButton.setText("Start")
        else:
            self.ui.label_timer.setText(f"{self.remaining_time} seconds")
            self.timer.start()
            self.ui.pushButton.setText("Stop")

if __name__ == "__main__":
    app = QApplication([])
    form = Lab1()
    form.show()
    sys.exit(app.exec_())