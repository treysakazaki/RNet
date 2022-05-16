from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QApplication

app = QCoreApplication.instance()
if app is None:
    app = QApplication([])

def main(dlg):
    dlg.show()
    try:
        from IPython.lib.guisupport import start_event_loop_qt4
        start_event_loop_qt4(app)
    except ImportError:
        app.exec_()
