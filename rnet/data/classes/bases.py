
from abc import ABC, abstractmethod


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
