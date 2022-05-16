from abc import ABC, abstractmethod
import os

import numpy as np
import pandas as pd

from rnet.data.loaders import MapLoader, ElevationLoader
from rnet.exceptions import require_qgis
from rnet.toolkits.coords import (
    get_bounds2d,
    get_elev,
    transform2d
    )
from rnet.toolkits.graph import (
    filter_connections,
    clean_points,
    reindex_points
    )


class Data(ABC):
    '''
    Base class for data.
    '''
    
    __slots__ = ['crs', 'name']
    
    def __init__(self, crs, name):
        self.crs = crs
        self.name = name
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: '{self.name}' (EPSG:{self.crs})>"
    
    @abstractmethod
    def dump(self):
        print(f'name: {self.name}', f'crs: EPSG:{self.crs}', sep='\n')
    
    @abstractmethod
    def render(self):
        pass


class MapData(Data):
    '''
    Class for representing map data.
    
    Parameters:
        vertices (pandas.DataFrame): Frame containing vertex data.
        links (pandas.DataFrame): Frame containing link data.
    
    Keyword arguments:
        crs (int): EPSG code of the CRS in which vertex coordinates are
            represented.
        name (str): Data source name.
    
    Attributes:
        vertices (pandas.DataFrame): Frame containing vertex data.
        links (pandas.DataFrame): Frame containing link data.
        vertex_count (int): Number of vertices.
        link_count (int): Number of links.
    '''
    
    __slots__ = ['vertices', 'links', 'vertex_count', 'link_count']
    
    def __init__(self, vertices, links, *, crs, name):
        self.vertices = vertices
        self.links = links
        self.vertex_count = len(vertices)
        self.link_count = len(links)
        super().__init__(crs, name)
    
    def bounds(self):
        '''
        Return the coordinates that define the bounding box for the set of
        vertices.
        
        Returns:
            Tuple[float]: 4-tuple of the form (``xmin``, ``ymin``, ``xmax``,
            ``ymax``).
        '''
        return get_bounds2d(self.vertices.to_numpy())
    
    def dump(self):
        '''
        Print information about the instance.
        '''
        super().dump()
        print(f'vertex_count: {self.vertex_count:,}',
              f'link_count: {self.link_count:,}', sep='\n')
    
    def out(self, *, crs=None, include='all', exclude=None, keep_indices=False):
        '''
        Export vertex and link data frames.
        
        Keyword arguments:
            crs (:obj:`int`, optional): EPSG code of CRS for vertex coordinates.
                If different from ``.crs``, coordinates are transformed to `crs`.
                If None, coordinates are not transformed. Default: None.
            include (`'all'` or :obj:`List[str]`, optional): List of tags to
                include. If 'all', all tags are included. Default: 'all'.
            exclude (:obj:`List[str]`, optional): List of tags to exclude. If
                None, no tags are excluded. Default: None.
        
        Returns:
            Tuple[pandas.DataFrame, pandas.DataFrame]: 2-tuple containing
            ``.vertices`` and ``.links`` frames with links filtered and vertices
            transformed.
        
        Note:
            The keyword `include` takes precedence over `exclude`.
        '''
        # Copy frames
        vertices = self.vertices.copy()
        links = self.links.copy()
        # Filter links
        if include != 'all' or exclude is not None:
            if include != 'all':
                links = filter_connections(links, 'include', include)
            elif exclude is not None:
                links = filter_connections(links, 'exclude', exclude)
            vertices = clean_points(vertices, links)
            if not keep_indices:
                vertices, links = reindex_points(vertices, links)
        # Transform vertex coordinates
        if crs is None:
            pass
        elif crs != self.crs:
            coords = transform2d(vertices.to_numpy(), self.crs, crs)
            vertices['x'] = coords[:,0]
            vertices['y'] = coords[:,1]
        return vertices, links
    
    @require_qgis
    def render(self):
        pass
    
    @classmethod
    def from_osm(cls, path_to_osm, **kwargs):
        '''
        Instantiate class from an OSM data source.
        
        Parameters:
            path_to_osm (str): Path to OSM file.
    
        Keyword arguments:
            include (:obj:`List[str]`, optional): List of tags to include. All
                tags are included by default.
            exclude (:obj:`List[str]`, optional): List of tags to exclude. No
                tags are excluded by default.
        
        Other parameters:
            name (:obj:`str`, optional): Data source name. If unspecified, then
                the OSM file name is used.
        
        Note:
            If required, either the `include` or `exclude` keyword should be
            given, not both. In the case that both are given, `include` takes
            precedence and `exclude` is ignored.
        '''
        vertices, links = MapLoader.from_osm(path_to_osm)
        if 'include' in kwargs:
            links = filter_connections(links, 'include', kwargs['include'])
            vertices = clean_points(vertices, links)
            vertices, links = reindex_points(vertices, links)
        elif 'exclude' in kwargs:
            links = filter_connections(links, 'exclude', kwargs['exclude'])
            vertices = clean_points(vertices, links)
            vertices, links = reindex_points(vertices, links)
        name = kwargs.get('name', os.path.basename(path_to_osm))
        return cls(vertices, links, crs=4326, name=name)
    
    @classmethod
    def from_csvs(cls, path_to_dir, crs, **kwargs):
        pass


class ElevationData(Data):
    '''
    Class for representing a grid of elevation data points.
    
    Parameters:
        x (:obj:`numpy.ndarray`, shape (`nx`,)): `x`-coordinates of grid.
        y (:obj:`numpy.ndarray`, shape (`ny`,)): `y`-coordinates of grid.
        z (:obj:`numpy.ndarray`, shape (`ny`, `nx`)): Array of `z`-coordinates.
    
    Keyword arguments:
        crs (int): EPSG code of CRS in which :math:`(x, y)` coordinates are
            represented.
        name (str): Data source name.
    
    Attributes:
        x (:obj:`numpy.ndarray`, shape (`nx`,)): `x`-coordinates of grid.
        y (:obj:`numpy.ndarray`, shape (`ny`,)): `y`-coordinates of grid.
        z (:obj:`numpy.ndarray`, shape (`ny`, `nx`)): Array of `z`-coordinates.
        nx (int): Grid width.
        ny (int): Grid height.
        point_count (int): Number of data points.
        xmin (float): Minimum `x`-coordinate.
        xmax (float): Maximum `x`-coordinate.
        ymin (float): Minimum `y`-coordinate.
        ymax (float): Maximum `y`-coordinate.
        zmin (float): Minimum `z`-coordinate.
        zmax (float): Maximum `z`-coordinate.
    '''
    
    __slots__ = ['x', 'y', 'z', 'nx', 'ny', 'point_count', 'xmin', 'ymin',
                 'zmin', 'xmax', 'ymax', 'zmax']
    
    def __init__(self, x, y, z, *, crs, name):
        self.x = x
        self.y = y
        self.z = z
        self.nx = len(x)
        self.ny = len(y)
        self.point_count = self.nx * self.ny
        self.xmin, self.xmax = x[0], x[-1]
        if self.xmin > self.xmax:
            self.xmin, self.xmax = self.xmax, self.xmin
        self.ymin, self.ymax = y[0], y[-1]
        if self.ymin > self.ymax:
            self.ymin, self.ymax = self.ymax, self.ymin
        self.zmin, self.zmax = np.min(z), np.max(z)
        super().__init__(crs, name)
    
    def bounds(self):
        '''
        Return the coordinates that define the three-dimensional bounding box
        for the set of data points.
        
        Returns:
            Tuple[float]: 6-tuple of the form (``xmin``, ``ymin``, ``zmin``,
            ``xmax``, ``ymax``, ``zmax``).
        '''
        return self.xmin, self.ymin, self.zmin, self.xmax, self.ymax, self.zmax
    
    def dump(self):
        '''
        Print information about the instance.
        '''
        super().dump()
        print(f'point_count: {self.point_count:,}')
        for attr in ['xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax']:
            print(f'{attr}: {getattr(self, attr):,}')
    
    def get_elev(self, x, y, *, r=0.001, p=2):
        '''
        Return elevation at a single point.
        
        Parameters:
            x (float): `x`-coordinate.
            y (float): `y`-coordinate.
        
        Keyword Arguments:
            r (:obj:`float`, optional): Radius for neighboring point search.
                Default: 0.001.
            p (:obj:`int`, optional): Power setting for IDW interpolation.
                Default: 2.
        
        Returns:
            float: Elevation at point :math:`(x, y)`.
        
        See Also:
            :meth:`get_elevs`
                Returns elevations at multiple points.
        '''
        return get_elev(self.x, self.y, self.z, x, y, r, p)
    
    def get_elevs(self, points, *, r=0.001, p=2):
        '''
        Return elevations at multiple points.
        
        Parameters:
            points (:obj:`numpy.ndarray`, shape (`N`, 2)): The `N` points at
                which to compute elevations.
        
        Keyword Arguments:
            r (:obj:`float`, optional): Radius for neighbor search. Default: 50.
            p (:obj:`int`, optional): Power setting. Default: 2.
        
        Returns:
            List[float]: elevations
                ``elevations[i]`` is the elevation at ``points[i]``.
        
        See Also:
            :meth:`get_elev`
                Returns elevation at a single point.
        '''
        return np.array(list(
            map(lambda xy: self.get_elev(xy[0], xy[1], r=r, p=p), points)))
    
    def out(self):
        '''
        Export data frame with index ``.y``, columns ``.x``, and values ``.z``.
        
        Returns:
            pandas.DataFrame: Frame with `y`-coordinates in index and
            `x`-coordinates in columns.
        '''
        return pd.DataFrame(self.z, index=self.y, columns=self.x)
    
    def query(self, i, j):
        '''
        Return elevation at (``x[i]``, ``y[j]``).
        
        Parameters:
            i (int): Row number.
            j (int): Column number.
        
        Returns:
            float:
        
        Raises:
            IndexError: If `i` or `j` is out of bounds.
        '''
        return self.x[j], self.y[i], self.z[i,j]
    
    @require_qgis
    def render(self):
        pass
    
    @classmethod
    def from_tif(cls, path_to_tif, **kwargs):
        '''
        Instantiate class from a TIF data source.
        
        Parameters:
            path_to_tif (str): Path to TIF file.
        
        Keyword arguments:
            name (:obj:`str`, optional): Data source name. If unspecified, TIF
                file name is used.
        '''
        x, y, z = ElevationLoader.from_tif(path_to_tif)
        name = kwargs.get('name', os.path.basename(path_to_tif))
        return cls(x, y, z, crs=4326, name=name)
    
    @classmethod
    def from_csv(cls, path_to_csv, **kwargs):
        pass
