
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
    
    Keyword arguments:
        crs (int): EPSG code of the CRS in which vertex coordinates are
            represented.
    '''
    
    def __init__(self, vertices, links, *, crs):
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
            given, not both.
        '''
        vertices, links = maploader.from_osm(path_to_osm)
        if len(kwargs) == 1:
            if 'include' in kwargs:
                links = filter_connections(links, 'include', kwargs['include'])
            elif 'exclude' in kwargs:
                links = filter_connections(links, 'exclude', kwargs['exclude'])
            vertices = clean_points(vertices, links)
            vertices, links = reindex_points(vertices, links)
        return cls(vertices, links, crs=4326)
