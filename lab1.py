import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *

from lab1_ui import *
class Lab1(QMainWindow):
    def __init__(self, *args):
        QMainWindow.__init__(self)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        window = loadUi("lab1.ui", self)
        self.setWindowTitle("arduino_sensors”)
        self.ui.pushButton.clicked.connect(self.mybuttonfunction)
        
    def mybuttonfunction():
        

if __name__ == "__main__":
    app = QApplication([])
    form = Lab1()
    form.show()
    sys.exit(app.exec_())