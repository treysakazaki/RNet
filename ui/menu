from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout
    )


class MainMenu(QDialog):
    
    BUTTON_HEIGHT =  40
    BUTTON_WIDTH  = 180
    LABEL_WIDTH   = 250
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('gistools — Main Menu')
        self.setMinimumSize(QSize(400, 350))
        self.default_font = self.font()
        self.default_font.setFamily('Calibri')
        self.setFont(self.default_font)
        
        # Header
        welcome = QLabel('Welcome to gistools!')
        font = QFont(self.default_font)
        font.setPointSize(12)
        welcome.setFont(font)
            
        # Buttons
        self.buttons = {
            'run_grapher' : QPushButton('Run grapher'),
            'run_pathopt' : QPushButton('Run pathopt'),
            'run_contours': QPushButton('Run contours')
            }
        for button in self.buttons.values():
            button.setAutoDefault(False)
            button.setFixedSize(self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
            font = QFont(self.default_font)
            font.setPointSize(9)
            button.setFont(font)
        
        # Layout
        layout = QVBoxLayout()
        layout.addWidget(welcome, alignment=Qt.AlignHCenter)
        layout.addSpacing(30)
        layout.addWidget(self.buttons['run_grapher'], alignment=Qt.AlignHCenter)
        layout.addSpacing(10)
        layout.addWidget(self.buttons['run_pathopt'], alignment=Qt.AlignHCenter)
        layout.addSpacing(10)
        layout.addWidget(self.buttons['run_contours'], alignment=Qt.AlignHCenter)
        layout.addStretch()
        layout.addWidget(self._create_button_box())
        self.setLayout(layout)
        
        # Connect buttons
        self._connect_buttons()
    
    def _connect_buttons(self):
        self.buttons['close'].clicked.connect(self.reject)
    
    def _create_button_box(self) -> QDialogButtonBox:
        box = QDialogButtonBox()
        self.buttons.update({
            'options': box.addButton('Options...', QDialogButtonBox.HelpRole),
            'close'  : box.addButton('Close', QDialogButtonBox.RejectRole)
            })
        self.buttons['options'].setAutoDefault(False)
        self.buttons['close'].setAutoDefault(False)
        return box


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dlg = MainMenu()
    dlg.show()
    sys.exit(app.exec_())


if __name__ == '__console__':
    dlg = MainMenu()
    dlg.show()
