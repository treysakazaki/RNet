
from itertools import count
import os
from rnet.data.classes.bases import Data, DataContainer
from rnet.data.loaders import maploader
from rnet.toolkits.coords import transform2d
from rnet.toolkits.graph import (
    filter_connections,
    clean_points,
    reindex_points,
    concatenate
    )


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
        vertices, links = maploader.from_osm(path_to_osm)
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


class MapDataContainer(DataContainer):
    '''
    Container for map data.
    '''
    
    __slots__ = []
    ident = count(0)
    
    def __init__(self, name=None):
        super().__init__(name)
    
    def add(self, source, crs=None):
        '''
        Adds map data to the container.
        
        Parameters:
            source (:obj:`str` or :obj:`MapData`): Either (1) path to OSM file,
                (2) path to directory containing ``vertices.csv`` and
                ``links.csv`` pair, or (3) ``MapData`` instance.
            crs (:obj:`int`, optional): EPSG code of the CRS in which vertex
                coordinates are represented. Required only if `source` is of
                type (2).
        '''
        if type(source) is str:
            if os.path.isfile(source):
                self.data.append(MapData.from_osm(source))
            elif os.path.isdir(source):
                assert crs is not None
                self.data.append(MapData.from_csvs(source, crs))
            else:
                return
        elif isinstance(source, MapData):
            self.data.append(source)
        else:
            return
    
    def out(self, *, assume_unique=False, **kwargs):
        '''
        Exports concatenated vertex and link data frames.
        
        Keyword arguments:
            assume_unique (:obj:`bool`, optional): 
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
        frames = [d.out(**kwargs) for d in self.data]
        vertices, links = concatenate(*frames)
        if assume_unique:
            pass
        else:
            pass
        return vertices, links

