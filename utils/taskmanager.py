'''
taskmanager.py

For running tasks sequentially.

Author: Kota Sakazaki
Date: February 23, 2022
'''

from qgis.core import QgsApplication, QgsTask
from qgis.utils import iface


queue = []


def next_task():
    global queue
    try:
        task = queue.pop(0)
    except IndexError:
        iface.statusBarIface().showMessage('Ready')
    else:
        iface.statusBarIface().showMessage(task.description())
        QgsApplication.taskManager().addTask(task)


def add_task(task: QgsTask):
    global queue
    task.taskCompleted.connect(next_task)
    queue.append(task)
    if QgsApplication.taskManager().count() == 0:
        next_task()
