from abc import ABC, abstractmethod
import os
from rnet.data.loaders import MapLoader, ElevationLoader
from rnet.toolkits.coords import (
    create_tree,
    get_bounds3d,
    get_elev,
    get_elevs,
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
    '''
    
    __slots__ = ['vertices', 'links', 'vertex_count', 'link_count']
    
    def __init__(self, vertices, links, *, crs, name):
        self.vertices = vertices
        self.links = links
        self.vertex_count = len(vertices)
        self.link_count = len(links)
        super().__init__(crs, name)
    
    def dump(self):
        super().dump()
        print(f'vertex_count: {self.vertex_count:,}',
              f'link_count: {self.link_count:,}', sep='\n')
    
    def out(self, *, crs=None, include='all', exclude=None):
        '''
        Exports vertex and link data frames.
        
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
            If required, either the `include` or `exclude` keyword should be
            specified, not both. In the case that both are given, `include`
            takes precedence and `exclude` is ignored.
        '''
        # Copy frames
        vertices = self.vertices.copy()
        links = self.links.copy()
        # Filter links
        if include != 'all':
            print('including')
            links = filter_connections(links, 'include', include)
            vertices = clean_points(vertices, links)
            vertices, links = reindex_points(vertices, links)
        elif exclude is not None:
            links = filter_connections(links, 'exclude', exclude)
            vertices = clean_points(vertices, links)
            vertices, links = reindex_points(vertices, links)
        # Transform vertex coordinates
        if crs is None:
            pass
        elif crs != self.crs:
            coords = transform2d(vertices.to_numpy(), self.crs, crs)
            vertices['x'] = coords[:,0]
            vertices['y'] = coords[:,1]
        return vertices, links
    
    def render(self):
        pass
    
    @classmethod
    def from_osm(cls, path_to_osm, **kwargs):
        '''
        Instantiate class from an OSM file.
        
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
    Class for representing elevation data.
    '''
    
    __slots__ = ['df', 'tree', 'point_count', 'xmin', 'ymin', 'zmin', 'xmax',
                 'ymax', 'zmax']
    
    def __init__(self, df, *, crs, name):
        self.df = df
        self.tree = create_tree(df[['x', 'y']].to_numpy())
        self.point_count = len(df)
        self.xmin, self.ymin, self.zmin, self.xmax, self.ymax, self.zmax = \
            get_bounds3d(df.to_numpy())
        super().__init__(crs, name)
    
    def dump(self):
        super().dump()
        print(f'point_count: {self.point_count:,}')
        for attr in ['xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax']:
            print(f'{attr}: {getattr(self, attr):,}')
    
    def get_elev(self, x, y, *, r=50, p=2):
        '''
        Returns elevation at a single point. The elevation is computed via
        inverse distance weighting (IDW) interpolation.
        
        Parameters:
            x (float): `x`-coordinate.
            y (float): `y`-coordinate.
        
        Keyword Arguments:
            r (:obj:`float`, optional): Radius for neighbor search. Default: 50.
            p (:obj:`int`, optional): Power setting. Default: 2.
        
        Returns:
            float:
        
        See Also:
            :meth:`get_elevs`
                Returns elevations at multiple points.
        '''
        return get_elev(self.df, self.tree, x, y, r, p)
    
    def get_elevs(self, points, *, r=50, p=2):
        '''
        Returns elevations at multiple points. The elevations are computed via
        inverse distance weighting (IDW) interpolation.
        
        Parameters:
            points (:obj:`numpy.ndarray`, shape(N,2)): The N points at which
                to compute elevations.
        
        Keyword Arguments:
            r (:obj:`float`, optional): Radius for neighbor search. Default: 50.
            p (:obj:`int`, optional): Power setting. Default: 2.
        
        Returns:
            List[float]:
        
        Warning:
            Points that are outside of the data bounds will return a
            corresponding elevation value of ``numpy.nan``.
        
        See Also:
            :meth:`get_elev`
                Returns elevation at a single point.
        '''
        return get_elevs(self.df, self.tree, points, r, p)
    
    def out(self, *, crs=None):
        '''
        Exports point data frame.
        
        Keyword arguments:
            crs (:obj:`int`, optional): EPSG code of CRS for point coordinates.
                If different from ``.crs``, coordinates are transformed to `crs`.
                If None, coordinates are not transformed. Default: None.
        
        Returns:
            pandas.DataFrame: ``.df`` frame with coordinates transformed.
        '''
        # Copy frames
        df = self.df.copy()
        # Transform vertex coordinates
        if crs is None:
            pass
        elif crs != self.crs:
            coords = transform2d(df[['x', 'y']].to_numpy(), self.crs, crs)
            df['x'] = coords[:,0]
            df['y'] = coords[:,1]
        return df
    
    def render(self):
        pass
    
    @classmethod
    def from_tif(cls, path_to_tif, **kwargs):
        df = ElevationLoader.from_tif(path_to_tif)
        name = kwargs.get('name', os.path.basename(path_to_tif))
        return cls(df, crs=4326, name=name)
    
    @classmethod
    def from_csv(cls, path_to_csv, **kwargs):
        pass
    
    @property
    def bounds(self):
        return (self.xmin, self.ymin, self.zmin, self.xmax, self.ymax, self.zmax)
