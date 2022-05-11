from abc import ABC, abstractmethod
from itertools import count
import os
from rnet.data.classes import MapData, ElevationData
from rnet.toolkits.graph import concatenate
from rnet.toolkits.coords import concatenate_points


class DataContainer(ABC):
    '''
    Base class for data containers.
    '''
    
    __slots__ = ['name', 'data']
    
    def __init__(self, name):
        if name is None:
            name = f'{self.__class__.__name__}_{str(next(self.ident))}'
        self.name = name
        self.data = []
    
    def __repr__(self):
        if self.source_count == 0:
            return f"<{self.__class__.__name__} (EMPTY)>"
        elif self.source_count == 1:
            return f"<{self.__class__.__name__} ({self.source_count} source)>"
        else:
            return f"<{self.__class__.__name__} ({self.source_count} sources)>"
    
    @abstractmethod
    def add(self):
        pass

    @property
    def source_count(self):
        return len(self.data)


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
                ``links.csv`` pair, or (3) :class:`MapData` instance.
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
    
    def out(self, *, assume_unique=False, crs=4326, include='all', exclude=None):
        '''
        Creates a :class:`MapData` instance containing concatenated frames.
        
        Keyword arguments:
            assume_unique (:obj:`bool`, optional): If True, vertices and links
                in all data sources are assumed to be unique. If False, data
                sources are checked for uniqueness and only unique features are
                retained. Default: False.
            crs (:obj:`int`, optional): EPSG code of CRS for vertex coordinates.
                Default: 4326.
            include (`'all'` or :obj:`List[str]`, optional): List of tags to
                include. If 'all', all tags are included. Default: 'all'.
            exclude (:obj:`List[str]`, optional): List of tags to exclude. If
                None, no tags are excluded. Default: None.
        
        Returns:
            MapData: MapData instance.
        
        See also:
            :class:`MapData`
                Class for representing map data.
        '''
        frames = [source.out(crs=crs, include=include, exclude=exclude)
                  for source in self.data]
        vertices, links = concatenate(*frames)
        if assume_unique:
            pass
        else:
            pass
        return MapData(vertices, links, crs=crs, name='Concatenated')


class ElevationDataContainer(DataContainer):
    '''
    Container for elevation data.
    '''
    
    __slots__ = []
    ident = count(0)
    
    def __init__(self, name=None):
        super().__init__(name)
    
    def add(self, source, crs=None):
        '''
        Adds elevation data to the container.
        
        Parameters:
            source (:obj:`str` or :obj:`ElevationData`): Either (1) path to
                TIF file, (2) path to CSV file, or (3) :class:`ElevationData`
                instance.
            crs (:obj:`int`, optional): EPSG code of the CRS in which point
                coordinates are represented. Required only if `source` is of
                type (2).
        '''
        if type(source) is str:
            if os.path.isfile(source):
                ext = os.path.splitext(source)[1]
                if ext == '.tif':
                    self.data.append(ElevationData.from_tif(source))
                elif ext == '.csv':
                    pass
            else:
                return
        elif isinstance(source, ElevationData):
            self.data.append(source)
        else:
            return
    
    def out(self, *, assume_unique=False, crs=4326):
        '''
        Creates an :class:`ElevationData` instance containing concatenated
        frames.
        
        Keyword arguments:
            assume_unique (:obj:`bool`, optional): If True, points in all data
                sources are assumed to be unique. If False, data sources are
                checked for uniqueness and only unique features are retained.
                Default: False.
            crs (:obj:`int`, optional): EPSG code of CRS for :math:`(x,y)`
                coordinates. Default: 4326.
        
        Returns:
            ElevationData: ElevationData instance.
        
        See also:
            :class:`ElevationData`
                Class for representing elevation data.
        '''
        frames = [source.out(crs=crs) for source in self.data]
        data = concatenate_points(*frames)
        if assume_unique:
            pass
        else:
            pass
        return ElevationData(data, crs=crs, name='Concatenated')

