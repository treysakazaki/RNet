from functools import wraps
from itertools import count
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from rnet.ui.progress import ProgressDialog


DLG = ProgressDialog()


def task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        worker = Worker.create('No description')
        worker.add('Description', func, *args, **kwargs)
        run_task(worker)
    return wrapper


class Worker(QObject):
    
    canceled = pyqtSignal()
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    label = pyqtSignal(str)
    ident = count(0)
    
    def __init__(self, description):
        super().__init__()
        self.description = description
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
    def create(cls, description):
        worker_name = f'{cls.__name__}_{str(next(cls.ident))}'
        globals()[worker_name] = cls(description)
        return globals()[worker_name]


def run_task(worker):
    DLG.canceled.connect(worker.cancel)
    DLG.show()
    
    global thread
    thread = QThread()
    worker.moveToThread(thread)
    
    thread.started.connect(worker.run)
    #thread.started.connect(lambda: dlg.show())
    
    worker.progress.connect(lambda v: DLG.setValue(v))
    worker.label.connect(lambda s: DLG.setLabelText(s))
    
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(lambda: DLG.close())
    
    worker.canceled.connect(thread.quit)
    worker.canceled.connect(worker.deleteLater)
    worker.canceled.connect(thread.deleteLater)
    
    thread.start()


if __name__ == '__console__':
    from time import sleep
    
    @task
    def dummy(t=5):
        print('start')
        sleep(t)
        print(f'slept for {t} secs')