from functools import partial
import gdal
import numpy as np
import pandas as pd
import time
from typing import List, Tuple, Union
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsMarkerSymbol,
    QgsPointXY,
    QgsProject,
    QgsRuleBasedRenderer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSpatialIndexKDBush,
    QgsTask,
    QgsVectorLayer
    )
from qgis.utils import iface


class Error(Exception):
    pass


class InvalidCRSError(Error):
    def __init__(self, crs: str):
        super().__init__(f"CRS '{crs}' is invalid")


class OutOfBoundsError(Error):
    def __init__(self, x: float, y: float):
        super().__init__(f'coordinate ({x}, {y}) is outside of extents')


class TransformCoords(QgsTask):
    '''
    Task for transforming coordinates.
    
    Parameters:
        xcoords (Union[List[float], pd.Series]) -- x-coordinates
        ycoords (Union[List[float], pd.Series]) -- y-coordinates
        src (str) -- source CRS
        dst (str) -- destination CRS
    '''
    
    def __init__(self, xcoords: Union[List[float], pd.Series],
                 ycoords: Union[List[float], pd.Series], src: str, dst: str):
        super().__init__('Transforming coordinates')
        srccrs = QgsCoordinateReferenceSystem(src)
        dstcrs = QgsCoordinateReferenceSystem(dst)
        if dstcrs.isValid():
            self.coords = list(zip(xcoords, ycoords))
            self.crs = dst
            self.ct = QgsCoordinateTransform(srccrs, dstcrs,
                                             QgsProject.instance())
        else:
            self.crs = src
            raise InvalidCRSError(dst)
    
    def run(self):
        new_coords = [tuple(self.ct.transform(x, y)) for (x, y) in self.coords]
        self.x, self.y = np.stack(new_coords, axis=1)
        return True
    
    def finished(self, success: bool):
        pass


class CreateLayer(QgsTask):
    '''
    Task for constructing a vector layer.
    
    Parameters:
        xcoords (Union[List[float], pd.Series]) -- x-coordinates
        ycoords (Union[List[float], pd.Series]) -- y-coordinates
        crs (str) -- CRS
    '''
    
    def __init__(self, xcoords: Union[List[float], pd.Series],
                 ycoords: Union[List[float], pd.Series], crs: str):
        super().__init__('Creating vector layer')
        self.xcoords = xcoords
        self.ycoords = ycoords
        self.crs = crs
        self.vl = QgsVectorLayer(f'point?crs={self.crs}', 'elevs', 'memory')
    
    def run(self):
        feats = []
        i, TOTAL = 0, len(self.xcoords)
        for (x, y) in zip(self.xcoords, self.ycoords):
            if self.isCanceled():
                return False
            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            feats.append(f)
            i += 1
            self.setProgress(i/TOTAL*99)
        self.vl.dataProvider().addFeatures(feats)
        self.setProgress(100)
        return True
    
    def finished(self, success: bool):
        pass


class CreateIndex(QgsTask):
    '''
    Task for constructing a 2D spatial index.
    
    Parameters:
        vl (QgsVectorLayer) -- vector layer
    '''
    
    def __init__(self, vl: QgsVectorLayer):
        super().__init__('Creating spatial index')
        self.vl = vl
    
    def run(self):
        self.index = QgsSpatialIndexKDBush(self.vl.getFeatures())
        return True
    
    def finished(self, success: bool):
        pass


class ElevData(QObject):
    
    crsUpdated = pyqtSignal()
    indexUpdated = pyqtSignal()
    layerUpdated = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.df = pd.DataFrame()
        self.crs = ''
    
    def info(self):
        print(self,
              *['{:5}: {}'.format(label, value) for label, value in [
                ('Count', f'{self.count:,} features'),
                ('XMin', f'{self.xmin:>15,.7f}'),
                ('XMax', f'{self.xmax:>15,.7f}'),
                ('YMin', f'{self.ymin:>15,.7f}'),
                ('YMax', f'{self.ymax:>15,.7f}'),
                ('ZMin', f'{self.zmin:7}'),
                ('ZMax', f'{self.zmax:7}')
                ]],
              sep='\n')
    
    def set_data(self, path_to_tif: str):
        d = 1/3600  # 1 [arcsec] in [deg]
        r = gdal.Open(path_to_tif)
        t = r.GetGeoTransform()
        x0, y0 = t[0], t[3]
        dx, dy = t[1], t[5]
        assert np.abs(dx) == np.abs(dy) == d
        data = r.GetRasterBand(1).ReadAsArray()
        h, w = data.shape
        x = np.array([x0+i*dx for i in np.arange(w)]*h)
        y = np.array([[y0+j*dy]*w for j in np.arange(h)]).flatten()
        z = data.flatten()
        indices = np.argwhere(z > -32767).flatten()
        x = x[indices]
        y = y[indices]
        z = z[indices]
        self.df = pd.DataFrame.from_dict({'x': x, 'y': y, 'z': z})
        self.crs = 'EPSG:4326'
    
    def set_crs(self, dst: str):
        global task
        task = TransformCoords(self.df['x'], self.df['y'], self.crs, dst)
        task.begun.connect(
            lambda: iface.statusBarIface().showMessage(task.description()))
        task.taskCompleted.connect(partial(self._transform_complete, task))
        QgsApplication.taskManager().addTask(task)
    
    def show(self):
        '''
        Adds scratch layer containing data points to project.
        '''
        s = QgsMarkerSymbol()
        s.setSize(1.0)
        r = QgsRuleBasedRenderer(s)
        rule = r.rootRule().children()[0]
        rule.setMaximumScale(1.0)
        rule.setMinimumScale(15000.0)
        lyr = rule.symbol().symbolLayer(0)
        lyr.setShape(QgsSimpleMarkerSymbolLayerBase.Cross)
        lyr.setStrokeColor(QColor.fromRgb(255, 1, 1))
        self.vl.setRenderer(r)
        QgsProject.instance().addMapLayer(self.vl)
    
    def _transform_complete(self, task: TransformCoords):
        self.df['x'] = task.x
        self.df['y'] = task.y
        self.crs = task.crs
        self.crsUpdated.emit()
        iface.statusBarIface().showMessage('Ready')
    
    def update_index(self):
        global task
        task = CreateIndex(self.vl)
        task.begun.connect(
            lambda: iface.statusBarIface().showMessage(task.description()))
        task.taskCompleted.connect(partial(self._updated_index, task))
        QgsApplication.taskManager().addTask(task)
    
    def _updated_index(self, task: CreateIndex):
        self.index = task.index
        self.indexUpdated.emit()
        iface.statusBarIface().showMessage('Ready')
    
    def update_layer(self):
        '''
        Starts task for updating vector layer. The vector layer contains 2D
        points contained in the data frame.
        '''
        global task
        task = CreateLayer(self.df['x'], self.df['y'], self.crs)
        task.begun.connect(
            lambda: iface.statusBarIface().showMessage(task.description()))
        task.taskCompleted.connect(partial(self._updated_layer, task))
        QgsApplication.taskManager().addTask(task)
    
    def _updated_layer(self, task: CreateLayer):
        self.vl = task.vl
        self.layerUpdated.emit()
        iface.statusBarIface().showMessage('Ready')
    
    @property
    def count(self):
        return len(self.df)
    
    @property
    def xmax(self):
        '''Maximum x-coordinate.'''
        return max(self.df['x'])
    
    @property
    def xmin(self):
        '''Minimum x-coordinate.'''
        return min(self.df['x'])
    
    @property
    def ymax(self):
        '''Maximum y-coordinate.'''
        return max(self.df['y'])
    
    @property
    def ymin(self):
        '''Minimum y-coordinate.'''
        return min(self.df['y'])
    
    @property
    def zmax(self):
        '''Maximum z-coordinate.'''
        return max(self.df['z'])
    
    @property
    def zmin(self):
        '''Minimum z-coordinate.'''
        return min(self.df['z'])


class ElevUtils(ElevData):
    
    def __init__(self, path_to_tif: str, crs: str = 'EPSG:4326'):
        super().__init__()
        self.set_data(path_to_tif)
        if crs != 'EPSG:4326':
            self.set_crs(crs)
            self.crsUpdated.connect(self.update_layer)
        else:
            self.update_layer()
        self.layerUpdated.connect(self.update_index)
    
    def get_elev(self, x: float, y: float, r: int = 100, p: int = 1,
                 verbose: bool = False):
        '''
        Returns elevation at point (x, y).
        
        Parameters:
            x (float) -- x-coordinate
            y (float) -- y-coordinate
            r (int) -- search radius
            p (int) -- power setting
            verbose (bool) -- prints details to console if True
        '''
        if verbose: start = time.time()
        if np.all([self.xmin <= x <= self.xmax, self.ymin <= y <= self.ymax]):
            ngbrs = [d.id for d in self.index.within(QgsPointXY(x, y), r)]
            d = []
            z = []
            for n in ngbrs:
                xn, yn, zn = self.df.iloc[n][['x', 'y', 'z']]
                d.append(np.linalg.norm([x - xn, y - yn]))
                z.append(zn)
            z = np.array(z)
            d = np.power(np.array(d), p)
            if verbose:
                print(f'x={x}', f'y={y}', f'found {len(ngbrs)} neighbors',
                      f'took {time.time()-start:.4f} s.', sep=', ')
            return np.sum(z/d) / np.sum(1/d)
        else:
            raise OutOfBoundsError(x, y)
    
    def get_elevs(self, points: List[Tuple[float, float]], r: int = 100,
                  p: int = 1, verbose: bool = False):
        '''
        Returns elevations at points in list.
        
        Parameters
            points (List[Tuple[float, float]]) -- list of x-y coordinates
            r (int) -- search radius
            p (int) -- power setting
            verbose (bool) -- prints details to console if True
        '''
        return [self.get_elev(x, y, r, p, verbose) for (x, y) in points]
