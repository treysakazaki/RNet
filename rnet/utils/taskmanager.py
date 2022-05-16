from functools import wraps
from itertools import count
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from rnet.ui import dialogs
from rnet.ui.progress import ProgressDialog


def task(description, show_dlg=True, progress=False):
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            worker = Worker.create()
            worker.add(f'{description}...', func, *args, **kwargs)
            run_task(worker, show_dlg, progress)
        return inner
    return outer


class Worker(QObject):
    
    canceled = pyqtSignal()
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    label = pyqtSignal(str)
    ident = count(0)
    
    def __init__(self):
        super().__init__()
        self.queue = []
    
    def run(self):
        self.isCanceled = False
        for (label, func, args, kwargs) in self.queue:
            self.label.emit(label)
            func(*args, **kwargs)
            if self.isCanceled:
                self.canceled.emit()
                return
        self.finished.emit()
    
    def add(self, label, func, *args, **kwargs):
        self.queue.append((label, func, args, kwargs))
    
    def cancel(self):
        self.isCanceled = True
    
    @classmethod
    def create(cls):
        worker_name = f'Worker_{str(next(cls.ident))}'
        globals()[worker_name] = cls()
        return globals()[worker_name]


def run_task(worker, show_dlg, progress):
    if show_dlg:
        DLG = ProgressDialog()
        DLG.canceled.connect(worker.cancel)
        if progress:
            pass
        else:
            DLG.setMaximum(0)
        dialogs.main(DLG)
    
    global thread
    thread = QThread()
    worker.moveToThread(thread)
    
    thread.started.connect(worker.run)
    
    if show_dlg:
        worker.progress.connect(lambda v: DLG.setValue(v))
        worker.label.connect(lambda s: DLG.setLabelText(s))
    
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    
    if show_dlg:
        thread.finished.connect(lambda: DLG.close())
    
    worker.canceled.connect(thread.quit)
    worker.canceled.connect(worker.deleteLater)
    worker.canceled.connect(thread.deleteLater)
    
    thread.start()
