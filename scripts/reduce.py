'''
reduce.py   For reducing models to a small geographic region.

Author: Kota Sakazaki
Date: January 25, 2022
'''


from typing import List, Tuple
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsFields,
    QgsGeometry,
    QgsMessageLog,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsTask,
    QgsVectorLayer,
    QgsWkbTypes
    )
from qgis.utils import iface
from PyQt5.QtCore import pyqtSignal


class Reduce(QgsTask):
    '''
    Task for taking elements from a specified extent.
    
    Parameters:
        xmin (float) -- minimum x-coordinate
        ymin (float) -- minimum y-coordinate
        xmax (float) -- maximum x-coordinate
        ymax (float) -- maximum y-coordinate
        overwrite (bool = True) -- if True and a group named 'reduced' already
            exists, then the existing group is replaced by a new one
    '''
    
    reducing = pyqtSignal(str)
    
    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float,
                 overwrite: bool = True):
        super().__init__('Reducing layers')
        self.rect = QgsRectangle(xmin, ymin, xmax, ymax)
        # Find layers within 'gistools' group.
        root = QgsProject.instance().layerTreeRoot()
        gistools_group = root.findGroup('gistools')
        if gistools_group is None:
            QgsMessageLog.logMessage(
                "Couldn't find 'gistools' group.", 'gistools', Qgis.Critical)
        else:
            QgsMessageLog.logMessage(
                "Found 'gistools' group.", 'gistools', Qgis.Info)
        self.layers = {lyr.name(): lyr.layer()
                       for lyr in gistools_group.findLayers()}
        QgsMessageLog.logMessage(
            f'Found {len(self.layers)} layers to reduce.', 'gistools', Qgis.Info)
        # Create 'reduced' group.
        if overwrite:
            reduced_group = root.findGroup('reduced')
            if reduced_group is None:
                pass
            else:
                root.removeChildNode(reduced_group)
                QgsMessageLog.logMessage(
                    "Removed existing 'reduced' group.", 'gistools', Qgis.Info)
        self.reduced_group = root.insertGroup(0, 'reduced')
        QgsMessageLog.logMessage(
            "Created new 'reduced' group.", 'gistools', Qgis.Info)
        # Connect signal
        self.reducing.connect(
            lambda name: iface.statusBarIface().showMessage(f'Reducing {name}'))
    
    def run(self) -> bool:
        # Verify that given extent is valid.
        if self.rect.isNull():
            QgsMessageLog.logMessage(
                'Given extent is invalid.', 'gistools', Qgis.Critical)
            return False
        else:
            QgsMessageLog.logMessage(
                f'Reducing layers to extent {self.rect.toString(7)}',
                'gistools', Qgis.Info)
        # Reduce layers to specified extent.
        self.new_layers = []
        for name, lyr in self.layers.items():
            self.reducing.emit(name)
            # Create memory layer
            uri = '{}?crs={}'.format(QgsWkbTypes.displayString(lyr.wkbType()),
                                     lyr.crs().authid())
            vl = QgsVectorLayer(uri, name, 'memory')
            pr = vl.dataProvider()
            pr.addAttributes(QgsFields(lyr.fields()))
            vl.updateFields()
            # Add features
            pr.addFeatures(list(lyr.getFeatures(self.rect)))
            vl.updateExtents()
            # Record layer
            vl.setRenderer(lyr.renderer().clone())
            self.new_layers.append(vl)
            QgsMessageLog.logMessage(
                f"Reduced {name} ({vl.featureCount():,} remaining features)",
                'gistools', Qgis.Info)
        return True
    
    def finished(self, success: bool):
        if success:
            for vl in self.new_layers:
                QgsProject.instance().addMapLayer(vl, False)
                self.reduced_group.addLayer(vl)
            QgsMessageLog.logMessage(
                'Reduction complete.', 'gistools', Qgis.Success)
        else:
            QgsMessageLog.logMessage(
                'Reduction failed.', 'gistools', Qgis.Critical)
        iface.statusBarIface().clearMessage()
    
    @classmethod
    def from_points(cls, points: List[Tuple[float, float]], margin: float = 0,
                    overwrite: bool = True):
        bb = QgsGeometry.fromMultiPointXY(
            [QgsPointXY(*p) for p in points]).boundingBox()
        bb.grow(margin)
        xmin = bb.xMinimum()
        ymin = bb.yMinimum()
        xmax = bb.xMaximum()
        ymax = bb.yMaximum()
        return cls(xmin, ymin, xmax, ymax, overwrite)
