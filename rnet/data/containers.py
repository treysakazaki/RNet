
from abc import ABC, abstractmethod
from itertools import count
import os
from rnet.data.classes import MapData
from rnet.toolkits.graph import concatenate


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
    
    def out(self, *, assume_unique=False, **kwargs):
        '''
        Exports concatenated vertex and link data frames.
        
        Keyword arguments:
            assume_unique (:obj:`bool`, optional): If True, vertices and links
                in all data sources are assumed to be unique. If False, data
                sources are checked for uniqueness and only unique features are
                retained. Default: False.
        
        Other parameters:
            **kwargs: Parameters passed to ``MapData.out()``.
        
        Returns:
            Tuple[pandas.DataFrame, pandas.DataFrame]: 2-tuple containing
            ``.vertices`` and ``.links`` frames with links filtered and vertices
            transformed.
        
        See also:
            :meth:`MapData.out`
        '''
        frames = [d.out(**kwargs) for d in self.data]
        vertices, links = concatenate(*frames)
        if assume_unique:
            pass
        else:
            pass
        return vertices, links

