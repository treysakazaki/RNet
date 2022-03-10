'''
grapher.py

Author: Kota Sakazaki
Date: March 9, 2022
'''

from collections import defaultdict
from functools import partial
from typing import List, Union
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnchoredText
import numpy as np
import pandas as pd

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsTask,
    QgsVectorLayer
    )

from rnet.utils import taskmanager


# Tags pertaining to roads that are passable by a vehicle.
# Reference: https://wiki.openstreetmap.org/wiki/Key:highway
passable_roads = {
    'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
    'residential', 'motorway_link', 'trunk_link', 'primary_link',
    'secondary_link', 'tertiary_link', 'living_street'}


class Graph:
    
    ident = 0
    
    def __init__(self, name: str = None, crs: int = 4326):
        if name is None:
            self.name = self.get_next_ident()
        else:
            self.name = name
        self.crs = crs
        self.osm_ids = np.array([], dtype=int)
        self.vertices = pd.DataFrame(columns=['x', 'y'])
        self.links = pd.DataFrame(columns=['i', 'j', 'tag'])
        self.nodes = pd.DataFrame(columns=['x', 'y'])
        self.edges = pd.DataFrame(columns=['i', 'j', 'vseq', 'length', 'tag'])
        Graph.ident += 1
    
    def add_data(self, src: str):
        '''
        Add data from one or more OSM files to the Graph.
        
        Parameters:
            src (str) -- path to OSM file
        '''
        assert os.path.exists(src)
        # Load OSM data
        task_name = OsmLoader.get_next_ident()
        globals()[task_name] = OsmLoader(src)
        taskmanager.add_task(globals()[task_name])
        loader = globals()[task_name]
        # Add loaded data to Graph
        task_name = AddOsmData.get_next_ident()
        globals()[task_name] = AddOsmData(self, loader)
        taskmanager.add_task(globals()[task_name])
    
    def export(self, dir: str, overwrite: bool = False):
        assert os.path.isdir(dir)
        if not os.path.exists(dir):
            os.mkdir(dir)
        if not overwrite:
            names = {'vertices.csv', 'links.csv', 'nodes.csv'}
            existing = os.listdir(dir)
            if not names.isdisjoint(existing):
                raise FileExistsError(str(names.intersection(existing))[1:-1])
        self.vertices.to_csv(os.path.join(dir, 'vertices.csv'))
        self.links.to_csv(os.path.join(dir, 'links.csv'))
        self.nodes.to_csv(os.path.join(dir, 'nodes.csv'))
    
    def info(self):
        print('{:14}: {:>9}'.format('name', self.name))
        print('{:14}: {:>9}'.format('crs', self.crs))
        for k, v in self.properties().items():
            print(f'{k:14}: {v:>9,}')
    
    def plot(self, s: int = 25):
        plt.scatter(*np.stack(self.nodes.to_numpy(), axis=1),
                    s=s, c='#a2d418', edgecolors='k')
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.tick_params(direction='in', top=True, right=True)
        ax = plt.gca()
        ax.set_aspect('equal')
        plt.tight_layout()
        text = AnchoredText(f'[EPSG:{self.crs}]', loc=4)
        ax.add_artist(text)
        plt.show()
    
    def properties(self):
        class_items = self.__class__.__dict__.items()
        return {k: getattr(self, k)
                for k, v in class_items if isinstance(v, property)}
    
    def transform(self, crs: int):
        ct = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem(self.crs),
                QgsCoordinateReferenceSystem(crs),
                QgsProject.instance())
        transformed = [tuple(ct.transform(x, y))
                       for (x, y) in self.vertices.to_numpy()]
        x, y = np.stack(transformed, axis=1)
        self.vertices['x'] = x
        self.vertices['y'] = y
        m = np.isin(self.vertices.index, self.nodes.index, assume_unique=True)
        self.nodes = self.vertices.loc[m]
        self.crs = crs
    
    @classmethod
    def get_next_ident(cls):
        return '_'.join([cls.__name__, str(cls.ident)])
    
    @property
    def edge_count(self):
        return len(self.edges)
    
    @property
    def link_count(self):
        return len(self.links)
    
    @property
    def node_count(self):
        return len(self.nodes)
    
    @property
    def road_count(self):
        return len(self.osm_ids)
    
    @property
    def vertex_count(self):
        return len(self.vertices)


class OsmLoader(QgsTask):
    '''
    Task for loading data from an OSM file.
    
    Attributes:
        src (str) -- path to OSM file
        osm_ids (Set[int]) -- set of OSM feature IDs
        vertices (pandas.DataFrame) -- table of vertices
        links (pandas.DataFrame) -- table of links
    
    Class attributes:
        ident (int) -- for keeping track of the number of instantiations
    
    Parameters:
        src (str) -- path to OSM file
    '''
    
    ident = 0
    
    def __init__(self, src: str):
        super().__init__(f'Loading OSM data')
        self.src = src
        self.osm_ids = np.array([], dtype=int)
        self.vertices = pd.DataFrame(columns=['x', 'y'])
        self.links = pd.DataFrame(columns=['i', 'j', 'tag'])
        OsmLoader.ident += 1
    
    def run(self) -> bool:
        if os.path.isdir(self.src):
            names = list(filter(lambda x: os.path.splitext(x)[1] == '.osm',
                                os.listdir(self.src)))
            paths = [os.path.join(self.src, name) for name in names]
        elif os.path.splitext(self.src)[1] == '.osm':
            paths = [self.src]
        else:
            paths = []
        
        ii, COUNT = 0, len(paths)
        for path in paths:
            if self.isCanceled():
                return False
            else:
                print(os.path.basename(path), end='')
            
            vl = QgsVectorLayer(path + '|layername=lines', 'lines', 'ogr')
            feats = [f for f in vl.getFeatures()]
            
            # Retain only passable roads
            feats = list(filter(
                lambda f: f.attribute('highway') in passable_roads, feats))
            
            # Retain only new roads
            feats = list(filter(lambda f: f.id() not in self.osm_ids, feats))
            print(f' - {len(feats):,} roads', end='')
            
            # OSM IDs
            self.osm_ids = np.union1d(self.osm_ids, [f.id() for f in feats])
            
            # Vertices
            vcoords = np.array(
                [np.array([tuple(x) for x in f.geometry().asPolyline()])
                 for f in feats])
            vertices, inverse = np.unique(
                np.concatenate(vcoords), return_inverse=True, axis=0)
            vertices = pd.DataFrame(vertices, columns=['x', 'y'])
            print(f' - {len(vertices):,} vertices', end='')
            
            # Append vertices
            offset = max(self.vertices.index, default=-1) + 1
            vertices.index += offset
            self.vertices = pd.concat([self.vertices, vertices])
            
            # Links
            ind = np.concatenate([[0], np.cumsum([len(r) for r in vcoords])])
            vseqs = [inverse[ind[k]:ind[k+1]] for k in range(len(ind) - 1)]
            links = np.array(
                [seq[k:k+2] for seq in vseqs for k in range(len(seq) - 1)])
            i, j = np.stack(links, axis=1)
            tags = [f.attribute('highway') for f in feats]
            tags = np.concatenate(
                np.array([np.array([tags[k]] * (len(vseqs[k]) - 1))
                          for k in range(len(vseqs))]))
            links = pd.DataFrame({'i': i, 'j': j, 'tag': tags})
            print(f' - {len(links):,} links')
            
            # Append links
            links['i'] += offset
            links['j'] += offset
            offset = max(self.links.index, default=-1) + 1
            links.index += offset
            self.links = pd.concat([self.links, links])
            
            # Update progress
            ii += 1
            self.setProgress(ii/COUNT*100)
        
        # Remove duplicate vertices
        vertices, inverse = np.unique(
            self.vertices.to_numpy(), return_inverse=True, axis=0)
        self.vertices.index = inverse[list(self.vertices.index)]
        self.vertices.drop_duplicates(inplace=True)
        self.vertices.sort_index(inplace=True)
        self.links['i'] = inverse[list(self.links['i'])]
        self.links['j'] = inverse[list(self.links['j'])]
        
        # Remove duplicate links
        self.links.drop_duplicates(inplace=True, ignore_index=True)
        
        return True
    
    def finished(self, success: bool):
        if success:
            pass
        elif self.isCanceled():
            print('Task canceled.')
    
    @classmethod
    def get_next_ident(cls):
        return '_'.join([cls.__name__, str(cls.ident)])


class AddOsmData(QgsTask):
    '''
    Task for adding data loaded from OSM file(s) to Graph model.
    
    Parameters:
        G (Graph) -- Graph instance
        data (OsmLoader) -- OsmLoader instance
    '''
    
    ident = 0
    
    def __init__(self, G: Graph, data: OsmLoader):
        super().__init__('Adding OSM data')
        self.G = G
        self.data = data
        AddOsmData.ident += 1
    
    def run(self) -> bool:
        G, d = self.G, self.data
        print(f'{G.name}', end='')
        
        # Update OSM IDs
        G.osm_ids = np.union1d(G.osm_ids, d.osm_ids)
        
        # Transform vertex coordinates
        if G.crs != 4326:
            ct = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem(4326),
                QgsCoordinateReferenceSystem(G.crs),
                QgsProject.instance())
            transformed = [tuple(ct.transform(x, y))
                           for (x, y) in d.vertices.to_numpy()]
            x, y = np.stack(transformed, axis=1)
            d.vertices['x'] = x
            d.vertices['y'] = y
        
        # Append vertices
        offset = max(G.vertices.index, default=-1) + 1
        d.vertices.index += offset
        G.vertices = pd.concat([G.vertices, d.vertices])
        
        # Append links
        d.links['i'] += offset
        d.links['j'] += offset
        offset = max(G.links.index, default=-1) + 1
        d.links.index += offset
        G.links = pd.concat([G.links, d.links])
        
        # Remove duplicate vertices
        vertices, inverse = np.unique(
            G.vertices.to_numpy(), return_inverse=True, axis=0)
        G.vertices.index = inverse[list(G.vertices.index)]
        G.vertices.drop_duplicates(inplace=True)
        G.vertices.sort_index(inplace=True)
        G.links['i'] = inverse[list(G.links['i'])]
        G.links['j'] = inverse[list(G.links['j'])]
        print(f' - {len(G.vertices):,} vertices', end='')
        
        # Remove duplicate links
        G.links.drop_duplicates(inplace=True, ignore_index=True)
        print(f' - {len(G.links):,} links', end='')
        
        # Neighbors
        G.neighbors = defaultdict(set)
        for (i, j) in G.links[['i', 'j']].to_numpy():
            G.neighbors[i].add(j)
            G.neighbors[j].add(i)
        
        # Extract nodes
        nodes = set(i for i, n in G.neighbors.items() if len(n) != 2)
        m = np.isin(G.vertices.index, list(nodes), assume_unique=True)
        G.nodes = G.vertices.loc[m]
        print(f' - {len(G.nodes):,} nodes', end='')
        
        # Extract edges
        sequences = []
        leaves = {min(nodes)}
        new_leaves = set()
        history = set()
        visited = set()
        COUNT = len(nodes)
        while len(leaves) > 0:
            for o in leaves:
                for n in G.neighbors[o]:
                    if (o, n) in history:
                        continue
                    vseq, length = [o, n], 0.0
                    p, q = o, n
                    while q not in nodes:
                        x = list(G.neighbors[q].difference({p}))[0]
                        vseq.append(x)
                        p, q = q, x
                    sequences.append(tuple(vseq))
                    history.add((q, p))
                    new_leaves.add(q)
                visited.add(o)
                self.setProgress(len(visited)/COUNT*100)
            leaves = new_leaves.difference(visited)
            if len(leaves) == 0 and len(nodes) > len(visited):
                leaves = {min(nodes.difference(visited))}
        print(f' - {len(sequences):,} edges')
        
        return True
    
    def finished(self, success: bool):
        if not success:
            print('Error')
    
    @classmethod
    def get_next_ident(cls):
        return '_'.join([cls.__name__, str(cls.ident)])
