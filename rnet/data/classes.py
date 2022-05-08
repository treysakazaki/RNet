
from abc import ABC, abstractmethod
from itertools import count
import os
from rnet.data.loaders import MapLoader
from rnet.toolkits.coords import transform2d
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
        crs (int): EPSG code of the CRS in which vertex coordinates are
            represented.
    '''
    
    __slots__ = ['vertices', 'links', 'vertex_count', 'link_count']
    ident = count(0)
    
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
    
    def out(self, **kwargs):
        '''
        Exports vertex and link data frames.
        
        Keyword arguments:
            include (:obj:`List[str]`, optional): List of tags to include.
            exclude (:obj:`List[str]`, optional): List of tags to exclude.
            crs (:obj:`int`, optional): EPSG code of CRS for vertex coordinates.
                If different from ``.crs``, then vertex coordinates are
                transformed to the specified `crs`.
        
        Returns:
            Tuple[pandas.DataFrame, pandas.DataFrame]: 2-tuple containing
            ``.vertices`` and ``.links`` frames with links filtered and vertices
            transformed.
        
        Note:
            If required, either the `include` or `exclude` keyword should be
            given, not both. In the case that both are given, `include` takes
            precedence and `exclude` is ignored.
        '''
        # Copy frames
        vertices = self.vertices.copy()
        links = self.links.copy()
        # Filter links
        if 'include' in kwargs:
            links = filter_connections(links, 'include', kwargs['include'])
            vertices = clean_points(vertices, links)
            vertices, links = reindex_points(vertices, links)
        elif 'exclude' in kwargs:
            links = filter_connections(links, 'exclude', kwargs['exclude'])
            vertices = clean_points(vertices, links)
            vertices, links = reindex_points(vertices, links)
        # Transform vertex coordinates
        dstcrs = kwargs.get('crs', self.crs)
        if dstcrs != self.crs:
            coords = transform2d(vertices.to_numpy(), self.crs, dstcrs)
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
            include (:obj:`List[str]`, optional): List of tags to include.
            exclude (:obj:`List[str]`, optional): List of tags to exclude.
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


