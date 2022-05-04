
from rnet.data.loaders import maploader
from rnet.toolkits.graph import (
    filter_connections,
    clean_points,
    reindex_points
    )


class MapData:
    '''
    Class for representing map data.
    
    Parameters:
        vertices (pandas.DataFrame): Frame containing vertex data.
        links (pandas.DataFrame): Frame containing link data.
        crs (int): EPSG code of the CRS in which vertex coordinates are
            represented.
    '''
    
    def __init__(self, vertices, links, crs):
        self.crs = crs
        self.vertices = vertices
        self.links = links
        self.vertex_count = len(vertices)
        self.link_count = len(links)
    
    @classmethod
    def from_osm(cls, path_to_osm, **kwargs):
        '''
        Instantiate class from an OSM file.
        
        Parameters:
            path_to_osm (str): Path to OSM file.
    
        Keyword arguments:
            include (:obj:`List[str]`, optional): List of tags to include.
            exclude (:obj:`List[str]`, optional): List of tags to exclude.
        
        Note:
            If required, either the `include` or `exclude` keyword should be
            given, not both. In the case that both are given, `include` takes
            precedence and `exclude` is ignored.
        '''
        vertices, links = maploader.from_osm(path_to_osm)
        if len(kwargs) == 1:
            if 'include' in kwargs:
                links = filter_connections(links, 'include', kwargs['include'])
            elif 'exclude' in kwargs:
                links = filter_connections(links, 'exclude', kwargs['exclude'])
            vertices = clean_points(vertices, links)
            vertices, links = reindex_points(vertices, links)
        return cls(vertices, links, 4326)


class MapDataContainer:
    '''
    Container for map data.
    '''
    
    def __init__(self):
        self.data = []
    
    def add(self, *args):
        '''
        Adds map data to the container.
        
        Parameters:
            source (:obj:`str`, :obj:`Tuple[str, str, int]` or :obj:`MapData`):
                Either (1) path to OSM file, (2) 3-tuple containing paths to CSV
                files containing vertex and link data, followed by an EPSG code,
                or (3) ``MapData`` instance.
        '''
        if len(args) == 1:
            if type(args[0]) is str:
                self.data.append(MapData.from_osm(args[0]))
            elif isinstance(args[0], MapData):
                self.data.append(args[0])
            else:
                return
        elif len(args) == 3:
            try:
                assert type(args[0]) is str
                assert type(args[1]) is str
                assert type(args[2]) is int
            except AssertionError:
                return
            else:
                pass
        else:
            return

