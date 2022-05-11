from itertools import count
from networkx import Graph
import os
from rnet.data import MapDataContainer, ElevationDataContainer
from rnet.toolkits.graph import (
    compute_lengths,
    extract_nodes,
    extract_edges,
    reindex_points
    )
from rnet.utils.taskmanager import task


class Model:
    
    __slots__ = ['name', 'sources', 'built', 'crs', 'nodes', 'edges',
                 'node_count', 'edge_count']
    ident = count(0)
    
    def __init__(self, name=None):
        if name is None:
            name = '_'.join(['Model', str(next(self.ident))])
        self.name = name
        self.sources = {'maps': MapDataContainer(),
                        'elevations': ElevationDataContainer()}
        self.built = False
    
    def __repr__(self):
        return f"<Model '{self.name}' ({'' if self.built else 'un'}built)>"
    
    @task('Adding source')
    def add(self, source):
        if type(source) is str:
            if os.path.isfile(source):
                ext = os.path.splitext(source)[1]
                if ext == '.osm':
                    self.sources['maps'].add(source)
                elif ext == '.tif':
                    self.sources['elevations'].add(source)
            elif os.path.isdir(source):
                pass
        self.built = False
    
    @task('Building model')
    def build(self, *, crs=4326, include='all', exclude=None, r=5e-4, p=2):
        '''
        Keyword arguments:
            crs (:obj:`int`, optional): EPSG code for node coordinates. Default:
                4326.
            include ('all' or :obj:`List[str]`, optional): List of tags to
                include. If 'all', all tags are included. Default: 'all'.
            exclude (:obj:`List[str]`, optional): List of tags to exclude. If
                None, no tags are excluded. Default: None.
            r (:obj:`float`, optional): Radius for nearest neighbor search in
                IDW interpolation. Default: 0.0005.
            p (:obj:`int`, optional): Power setting for IDW interpolation.
                Default: 2.
        
        Note:
            The keyword `include` takes precedence over `exclude`.
        '''
        self.built = False
        if self.sources['maps'].source_count == 0:
            return
        # Retrieve vertices and links from map data
        md = self.sources['maps'].out(crs=crs, include=include, exclude=exclude)
        vertices, links = md.vertices, md.links
        # Compute elevations
        if self.sources['elevations'].source_count > 0:
            ed = self.sources['elevations'].out(crs=crs)
            vertices['z'] = ed.get_elevs(vertices.to_numpy(), r=r, p=p)
        # Compute link lengths
        links = compute_lengths(vertices, links)
        # Extract nodes and edges
        nodes = extract_nodes(vertices, links, False)
        edges = extract_edges(links, nodes, False)
        nodes, edges = reindex_points(nodes, edges)
        # Update attributes
        self.crs = crs
        self.nodes = nodes
        self.edges = edges
        self.node_count = len(nodes)
        self.edge_count = len(edges)
        self.built = True
    
    def dump(self):
        print(f'name: {self.name}')
        if self.built:
            print(f'crs: EPSG:{self.crs}', f'node_count: {self.node_count:,}',
                  f'edge_count: {self.edge_count:,}', sep='\n')

    def to_graph(self):
        G = Graph()
        G.add_nodes_from(self.nodes.index.tolist())
        G.add_edges_from(self.edges.index.tolist())
        return G
