
from itertools import count
from networkx import Graph
import os
from rnet.data.classes import MapDataContainer
from rnet.toolkits.graph import (
    compute_lengths,
    extract_nodes,
    extract_edges,
    reindex_points
    )


class Model:
    
    __slots__ = ['name', 'sources', 'built', 'crs', 'nodes', 'edges',
                 'node_count', 'edge_count']
    ident = count(0)
    
    def __init__(self, name=None):
        if name is None:
            name = '_'.join(['Model', str(next(self.ident))])
        self.name = name
        self.sources = {'maps': MapDataContainer()}
        self.built = False
    
    def __repr__(self):
        return f"<Model '{self.name}' ({'' if self.built else 'un'}built)>"
    
    def add(self, source):
        if type(source) is str:
            if os.path.isfile(source):
                ext = os.path.splitext(source)[1]
                if ext == '.osm':
                    self.sources['maps'].add(source)
    
    def build(self, **kwargs):
        crs = kwargs.setdefault('crs', 4326)
        if self.sources['maps'].source_count == 0:
            return
        # Retrieve vertices and links from map data
        vertices, links = self.sources['maps'].out(**kwargs)
        # Compute link lengths
        links = compute_lengths(vertices, links, 2)
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
