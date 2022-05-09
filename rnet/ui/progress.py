from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QProgressDialog


class ProgressDialog(QProgressDialog):
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Dialog|Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(300)
        self.setWindowTitle('RNet')
