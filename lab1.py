import sys
import random
from PyQt5.QtWidgets import *
from lab1_ui import *
import matplotlib

matplotlib.use("Qt5Agg")
from PyQt5.QtWidgets import QDialog
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class Lab1(QDialog):
    def __init__(self, *args):
        QDialog.__init__(self)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("arduino_sensors")


        # self.ui.verticalLayout = QVBoxLayout()
        # self.ui.verticalLayout.addWidget(NavigationToolbar(self.ui.MplWidget.canvas, self))
        # self.ui.MplWidget.setLayout(self.ui.verticalLayout)

        self.x = list(range(50)) 
        self.y = [random.randint(0, 10) for _ in range(50)] 

        self.ui.pushButton.clicked.connect(self.mybuttonfunction)

    def mybuttonfunction(self):
        self.ui.MplWidget.canvas.axes.clear()
        self.ui.MplWidget.canvas.axes.plot(self.x, self.y, 'r', linewidth=0.5)
        self.ui.MplWidget.canvas.draw()

if __name__ == "__main__":
    app = QApplication([])
    form = Lab1()
    form.show()
    sys.exit(app.exec_())