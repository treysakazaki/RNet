'''
contours.py    Utility functions for analyzing paths using contour data.

Author: Kota Sakazaki
Date: January 15, 2022
'''

import matplotlib.pyplot as plt
import numpy as np
from typing import List, Tuple
from qgis.core import (
    QgsApplication,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsSpatialIndexKDBush,
    QgsTask,
    QgsVectorLayer,
    QgsVectorLayerUtils
    )

# =======================
# User-defined parameters
# =======================

# The contour dataset for Ichihara city is very large. To conduct efficient
# queries of elevation, the user should work with small subsets of the map
# extents, defined by xmin, ymin, xmax, and ymax.

xmin =  18000
ymin = -60000
xmax =  28000
ymax = -55000


# =======================
# Model
# =======================

# Retrieve vector layers
# ----------------------

vl_vertices = QgsProject.instance().mapLayersByName('vertices')[0]
vl_nodes = QgsProject.instance().mapLayersByName('nodes')[0]
vl_edges = QgsProject.instance().mapLayersByName('edges')[0]
vl_contours = QgsProject.instance().mapLayersByName('contours')[0]


# Process data
# ------------

# Data is read from the vector layers and stored in the following attributes:
#     vertices (Dict[int, Tuple[float, float]]) -- vertex ID -> x-y coordinate
#     nodes (Set[int]) -- set of vertex IDs that are nodes
#     edges (Dict[Tuple[int, int], float]) -- (i, j) -> edge length
#     vseqs (Dict[Tuple[int, int], List[int]]) -- (i, j) -> vertex sequence
# After the data processing task finishes, these data will be accessible via
# attributes of the "data" variable, for instance, "data.vertices",
# "data.nodes", and so on.

class ProcessData(QgsTask):
    
    def __init__(self):
        super().__init__('Processing data')
        print('Processing data ...')
    
    def run(self) -> bool:
        
        self.vertices = dict(zip(
            QgsVectorLayerUtils.getValues(vl_vertices, 'fid')[0],
            list(zip(
                QgsVectorLayerUtils.getValues(vl_vertices, 'x')[0],
                QgsVectorLayerUtils.getValues(vl_vertices, 'y')[0]
                ))
            ))
        
        self.nodes = set(QgsVectorLayerUtils.getValues(vl_nodes, 'fid')[0])
        
        I = QgsVectorLayerUtils.getValues(vl_edges, 'i')[0]
        J = QgsVectorLayerUtils.getValues(vl_edges, 'j')[0]
        self.edges = dict(zip(
            list(zip(I + J, J + I)),
            QgsVectorLayerUtils.getValues(vl_edges, 'length')[0] * 2
            ))
        
        vseqs = dict(zip(
            list(zip(I, J)),
            QgsVectorLayerUtils.getValues(vl_edges, 'v_sequence')[0]
            ))
        self.vseqs = dict()
        for (i, j), s in vseqs.items():
            vseq = [int(x) for x in s[1:-1].split(', ')]
            self.vseqs.update({(i, j): vseq, (j, i): list(reversed(vseq))})
        
        return True
    
    def finished(self, success: bool):
        print('Finished processing data.')


if __name__ == '__console__':
    data = ProcessData()
    QgsApplication.taskManager().addTask(data)
    

# Create spatial index
# --------------------

# The spatial index allows for quick queries of elevation data.

class CreateIndex(QgsTask):
    
    def __init__(self):
        super().__init__('Creating spatial index')
        self.rect = QgsRectangle(xmin, ymin, xmax, ymax)
        print('Preparing utilities ...')
    
    def run(self) -> bool:
        # Create temporary layer
        uri = 'Point?crs=epsg:6677&field=Z:double&index=yes'
        self.vl = QgsVectorLayer(uri, 'zpoints', 'memory')
        fields = self.vl.fields()
        pr = self.vl.dataProvider()
        
        # Extract data points from 'contours' layer
        points = set()
        new_point_features = []
        FEATURE_COUNT = vl_contours.featureCount()
        print(f'Total contour count: {FEATURE_COUNT:,}')
        
        req = QgsFeatureRequest()
        req.setFilterRect(self.rect)
        req.setSubsetOfAttributes(['ELEV'], vl_contours.fields())
        FEATURE_COUNT = len(list(vl_contours.getFeatures(req)))
        print(f'Subset contour count: {FEATURE_COUNT:,}')
        
        progress = 0
        for f in vl_contours.getFeatures(req):
            if self.isCanceled():
                return False
            z = f.attribute('ELEV')
            for (x, y) in f.geometry().asPolyline():
                if (x, y, z) in points:
                    continue
                else:
                    feat = QgsFeature(fields)
                    feat.setAttributes([z])
                    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
                    new_point_features.append(feat)
                    points.add((x, y, z))
            progress += 1
            self.setProgress(progress / FEATURE_COUNT * 99)
        print(f'Point count: {len(points):,}')
        
        # Write points to temporary layer, then create spatial index
        print('Constructing index ...')
        pr.addFeatures(new_point_features)
        self.index = QgsSpatialIndexKDBush(self.vl.getFeatures())
        self.setProgress(100)
        print(f'Index size: {self.index.size():,}')
        
        return True
    
    def finished(self, success: bool):
        if success:
            global vl_zpoints
            vl_zpoints = self.vl
            QgsProject.instance().addMapLayer(vl_zpoints)
            print('Ready!')
        else:
            print('Task was canceled.')


if __name__ == '__console__':
    try:
        lyr_id = QgsProject.instance().mapLayersByName('zpoints')[0].id()
    except IndexError:
        pass
    else:
        QgsProject.instance().removeMapLayer(lyr_id)
    index = CreateIndex()
    QgsApplication.taskManager().addTask(index)


# =======================
# Utilities
# =======================

# Note: These utilities will only be available after the "CreateIndex" task
# completes construction of a spatial index.

def distance(x0: float, y0: float, xf: float, yf: float) -> float:
    '''
    Returns Euclidean distance between two points.
    
    Parameters:
        x0 (float) -- initial x-coordinate
        y0 (float) -- initial y-coordinate
        xf (float) -- final x-coordinate
        yf (float) -- final y-coordinate
    '''
    return np.linalg.norm(np.array([xf, yf]) - np.array([x0, y0]))


def get_elev(x: float, y: float, r: float = 50, p: int = 1):
    '''
    Computes the elevation at specified point via IDW interpolation.
    (Reference: https://gisgeography.com)
    
    Parameters:
        x (float) -- x-coordinate
        y (float) -- y-coordinate
        r (float = 50) -- radius from which to gather data points
        p (int = 1) -- IDW power setting
    '''
    try:
        assert xmin <= x <= xmax
        assert ymin <= y <= ymax
    except AssertionError:
        raise OutOfBoundsError(x, y)
    else:
        ngbrs = [d.id for d in index.index.within(QgsPointXY(x, y), r)]
        d = []
        z = []
        for f in vl_zpoints.getFeatures(ngbrs):
            d.append(np.linalg.norm(
                np.array([x, y]) - np.array(f.geometry().asPoint())) ** p)
            z.append(f.attribute('Z'))
        return np.sum(np.array(z) / np.array(d)) / np.sum(1 / np.array(d))


def nseq_to_vseq(nseq: list) -> list:
    '''
    Converts node sequence to vertex sequence.

    Parameters:
        nseq (list) -- sequence of node IDs

    Returns:
        vseq (list) -- sequence of vertex IDs
    '''
    vseq = [nseq[0]]
    for k in range(len(nseq) - 1):
        vseq.extend(data.vseqs[(nseq[k], nseq[k+1])][1:])
    return vseq


def nseq_to_points2D(nseq: list, d: float) -> List[Tuple[float, float]]:
    '''
    Inserts points along path at fixed interval.
    
    Parameters:
        vseq (list) -- list of vertex IDs
        d (float) -- interval (ground distance)
    
    Returns:
        points (List[Tuple[float, float]]) -- (x, y) coordinates
    '''
    v_coords = [data.vertices[v] for v in nseq_to_vseq(nseq)]
    points = []
    for k in range(len(v_coords) - 1):
        points.append(v_coords[k])
        (x0, y0), (xf, yf) = v_coords[k], v_coords[k+1]
        length = distance(x0, y0, xf, yf)
        phi = np.arctan2(yf - y0, xf - x0)
        r = d
        while r < length:
            points.append((x0 + r * np.cos(phi), y0 + r * np.sin(phi)))
            r += d
    points.append(v_coords[-1])
    return points


def nseq_to_points3D(nseq: list, d: float, r: float = 50, p: int = 1
                     ) -> List[Tuple[float, float, float]]:
    '''
    Inserts points along path at fixed interval.
    
    Parameters:
        vseq (list) -- list of vertex IDs
        d (float) -- interval (ground distance)
        r (float = 50) -- radius from which to gather data points
        p (int = 1) -- IDW power setting
    
    Returns:
        points (List[Tuple[float, float, float]]) -- (x, y, z) coordinates
    '''
    v_coords = [data.vertices[v] for v in nseq_to_vseq(nseq)]
    points = []
    for k in range(len(v_coords) - 1):
        points.append(v_coords[k])
        (x0, y0), (xf, yf) = v_coords[k], v_coords[k+1]
        length = distance(x0, y0, xf, yf)
        phi = np.arctan2(yf - y0, xf - x0)
        r = d
        while r < length:
            points.append((x0 + r * np.cos(phi), y0 + r * np.sin(phi)))
            r += d
    points.append(v_coords[-1])
    return [(x, y, get_elev(x, y, r, p))for (x, y) in points]


def node_indices(vseq: list) -> list:
    '''
    Returns indices at which vertex is in the set of nodes.
    
    Parameters:
        vseq (list) -- sequence of vertex IDs
    
    Returns:
        indices (list) -- sequence of indices
    '''
    indices = []
    for k in range(len(vseq)):
        if vseq[k] in data.nodes:
            indices.append(k)
    return indices


# =======================
# Plots
# =======================

def default_plot(xlabel: str, ylabel: str):
    '''
    Returns default figure and axes for plotting.
    
    Parameters:
        xlabel (str) -- x label
        ylabel (str) -- y label
    
    Returns:
        fig (matplotlib.figure.Figure) -- figure
        ax (matplotlib.axes._subplots.AxesSubplot) -- axes
    '''
    fig = plt.figure()
    ax = plt.axes()
    ax.tick_params(direction='in')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    return fig, ax


def plot_XY(nseq: list, show_vertices: bool = False, show_points: bool = False,
            d: float = None):
    '''
    Plots path on x-y plane.
    
    Parameters:
        nseq (list) -- sequence of node IDs
        show_vertices (bool = False) -- whether to display vertices
        show_points (bool = False) -- whether to display points
        d (bool = None) -- point interval, required if show_points is True
    '''
    fig, ax = default_plot('x (m)', 'y (m)')
    
    if show_points:
        try:
            assert d is not None
        except AssertionError:
            print('ERROR: point interval must be specified to plot points')
        else:
            points = nseq_to_points2D(nseq, d)
            ax.scatter([x for (x, _) in points], [y for (_, y) in points],
                       s=25, c='w', edgecolors='k', zorder=1)
    
    vseq = nseq_to_vseq(nseq)
    v_coords = [data.vertices[v] for v in vseq]
    n_coords = [v_coords[i] for i in node_indices(vseq)]
    
    if show_vertices:
        ax.scatter([x for (x, _) in v_coords], [y for (_, y) in v_coords],
                    s=25, c='#d5d5d5', edgecolors='k', zorder=2)
    
    ax.scatter([x for (x, _) in n_coords], [y for (_, y) in n_coords],
               s=25, c='#a2d418', edgecolors='k', zorder=3)
    
    ax.plot([x for (x, _) in v_coords], [y for (_, y) in v_coords],
            c='k', zorder=0)
    
    ax.axis('equal')
    fig.tight_layout()
    fig.show()


def plot_ZGD(nseq: list, d: float = 10, r: float = 50, p: int = 1):
    '''
    Plots elevation vs. ground distance for specified path.
    
    Parameters:
        nseq (list) -- sequence of node IDs
        d (float = 10) -- interval (ground distance)
        r (float = 50) -- radius from which to gather data points
        p (int = 1) -- IDW power setting
    '''
    points = nseq_to_points3D(nseq, d, r, p)
    z  = [p[2] for p in points]
    gd = [0.0]
    for k in range(len(z) - 1):
        gd.append(gd[-1] + distance(*points[k][:2], *points[k+1][:2]))
    
    fig, ax = default_plot('Ground distance (m)', 'Elevation (m)')
    ax.plot(gd, z, c='k', zorder=0)
    fig.tight_layout()
    fig.show()


# =======================
# Exceptions
# =======================

class Error(Exception):
    pass

class OutOfBoundsError(Error):
    def __init__(self, x: float, y: float):
        super().__init__(f'Point ({x}, {y}) is outside of user-defined extents.')
