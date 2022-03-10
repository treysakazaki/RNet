from collections import Counter, defaultdict
import os

from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnchoredText
import numpy as np
import pandas as pd

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsTask,
    QgsVectorLayer,
    QgsVectorLayerUtils
    )

from rnet.utils import taskmanager


# Tags pertaining to roads that are passable by a vehicle.
# Reference: https://wiki.openstreetmap.org/wiki/Key:highway
passable_roads = {
    'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
    'residential', 'motorway_link', 'trunk_link', 'primary_link',
    'secondary_link', 'tertiary_link', 'living_street'}


class Digraph:
    
    ident = 0
    
    def __init__(self, name: str = None, crs: int = 4326):
        if name is None:
            self.name = self.get_next_ident()
        else:
            self.name = name
        self.crs = crs
        self.osm_ids = np.array([], dtype=int)
        self.vertices = pd.DataFrame(columns=['x', 'y'])
        self.links = pd.DataFrame(columns=['i', 'j', 'length', 'tag'])
        self.nodes = pd.DataFrame(columns=['x', 'y'])
        self.edges = pd.DataFrame(columns=['i', 'j', 'vseq', 'length', 'tag'])
        Digraph.ident += 1
    
    def add_data(self, src: str):
        '''
        Add data from one or more OSM files to the Digraph.
        
        Parameters:
            src (str) -- path to OSM file
        '''
        assert os.path.exists(src)
        # Load OSM data
        task_name = OsmLoader.get_next_ident()
        globals()[task_name] = OsmLoader(src, self.crs)
        taskmanager.add_task(globals()[task_name])
        loader = globals()[task_name]
        # Add loaded data to Digraph
        task_name = AddOsmData.get_next_ident()
        globals()[task_name] = AddOsmData(self, loader)
        taskmanager.add_task(globals()[task_name])
    
    def export(self, dir: str, overwrite: bool = False):
        assert os.path.isdir(dir)
        if not os.path.exists(dir):
            os.mkdir(dir)
        if not overwrite:
            names = {'vertices.csv', 'links.csv', 'nodes.csv', 'edges.csv'}
            existing = os.listdir(dir)
            if not names.isdisjoint(existing):
                raise FileExistsError(str(names.intersection(existing))[1:-1])
        self.vertices.to_csv(os.path.join(dir, 'vertices.csv'))
        self.links.to_csv(os.path.join(dir, 'links.csv'))
        self.nodes.to_csv(os.path.join(dir, 'nodes.csv'))
        self.edges.to_csv(os.path.join(dir, 'edges.csv'))
    
    def info(self):
        print('{:14}: {:>9}'.format('name', self.name))
        print('{:14}: {:>9}'.format('crs', self.crs))
        for k, v in self.properties().items():
            print(f'{k:14}: {v:>9,}')
    
    def plot(self, s: int = 25):
        # Nodes
        plt.scatter(*np.stack(self.nodes.to_numpy(), axis=1),
                    s=s, c='#a2d418', edgecolors='k', zorder=1)
        # Edges
        for (i, j) in self.edges[['i', 'j']].to_numpy():
            _, vcoords = self.vseq(i, j, return_coords=True)
            plt.plot(*np.stack(vcoords, axis=1), color='k', zorder=0)
        # Appearance
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
    
    def show(self):
        global task
        task = Visualize(self)
        taskmanager.add_task(task)
    
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
    
    def vseq(self, i: int, j: int, return_coords: bool = False):
        '''
        Return the vertex sequence associated with edge (i, j).
        
        Parameters:
            i (int) -- node ID
            j (int) -- node ID
        
        Raises:
            KeyError if edge (i, j) does not exist.
        
        Return type:
            Tuple[int]
        '''
        if i < j:
            vseq = self.vseqs[(i, j)]
        else:
            vseq = tuple(reversed(self.vseqs[(j, i)]))
        if not return_coords:
            return vseq
        else:
            return vseq, self.vertices.loc[list(vseq)].to_numpy()
    
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
    
    def __init__(self, src: str, crs: int):
        super().__init__('Loading OSM data')
        self.src = src
        self.crs = crs
        self.osm_ids = np.array([], dtype=int)
        self.vertices = pd.DataFrame(columns=['x', 'y'])
        self.links = pd.DataFrame(columns=['i', 'j', 'length', 'tag'])
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
            ind = np.concatenate([[0], np.cumsum([len(r) for r in vcoords])])
            
            # Transform vertex coordinates
            if self.crs != 4326:
                ct = QgsCoordinateTransform(
                    QgsCoordinateReferenceSystem(4326),
                    QgsCoordinateReferenceSystem(G.crs),
                    QgsProject.instance())
                vcoords = [tuple(ct.transform(x, y))
                           for (x, y) in np.concatenate(vcoords)]
            
            # Remove duplicate vertices
            vertices, inverse = np.unique(vcoords, return_inverse=True, axis=0)
            vertices = pd.DataFrame(vertices, columns=['x', 'y'])
            print(f' - {len(vertices):,} vertices', end='')
            
            # Append vertices
            offset = max(self.vertices.index, default=-1) + 1
            vertices.index += offset
            self.vertices = pd.concat([self.vertices, vertices])
            
            # Links
            vseqs = [inverse[ind[k]:ind[k+1]] for k in range(len(ind) - 1)]
            links = np.array(
                [seq[k:k+2] for seq in vseqs for k in range(len(seq) - 1)])
            lengths = np.array([np.linalg.norm(np.diff(vcoords[k:k+2], axis=0))
                                for k in range(len(vcoords) - 1)])
            lengths = [lengths[ind[k]:ind[k+1]-1] for k in range(len(ind) - 1)]
            lengths = np.concatenate(lengths)
            tags = [f.attribute('highway') for f in feats]
            tags = np.concatenate(
                np.array([np.array([tags[k]] * (len(vseqs[k]) - 1))
                          for k in range(len(vseqs))]))
            i, j = np.stack(links, axis=1)
            links = pd.DataFrame(
                {'i': i, 'j': j, 'length': lengths, 'tag': tags})
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
    Task for adding data loaded from OSM file(s) to Digraph model.
    
    Parameters:
        G (Digraph) -- Digraph instance
        data (OsmLoader) -- OsmLoader instance
    '''
    
    ident = 0
    
    def __init__(self, G: Digraph, data: OsmLoader):
        super().__init__('Adding OSM data')
        self.G = G
        self.data = data
        AddOsmData.ident += 1
    
    def run(self) -> bool:
        G, d = self.G, self.data
        print(f'{G.name}', end='')
        
        # Update OSM IDs
        G.osm_ids = np.union1d(G.osm_ids, d.osm_ids)
        
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
        
        # Vertex neighbors, link lengths and tags
        G.neighbors = defaultdict(set)
        lengths = dict()
        tags = dict()
        for _, i, j, length, tag in G.links.to_records():
            G.neighbors[i].add(j)
            G.neighbors[j].add(i)
            lengths[(i, j)] = lengths[(j, i)] = length
            tags[(i, j)] = tags[(j, i)] = tag
        
        # Extract nodes
        nodes = set(i for i, n in G.neighbors.items() if len(n) != 2)
        m = np.isin(G.vertices.index, list(nodes), assume_unique=True)
        G.nodes = G.vertices.loc[m]
        print(f' - {len(G.nodes):,} nodes', end='')
        
        # Extract edges
        edges = []
        vseqs = []
        elens = []
        etags = []
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
                    vseq = [o, n]
                    p, q = o, n
                    while q not in nodes:
                        x = list(G.neighbors[q].difference({p}))[0]
                        vseq.append(x)
                        p, q = q, x
                    i, j = vseq[0], vseq[-1]
                    if i > j:
                        i, j = j, i
                        vseq.reverse()
                    edges.append((i, j))
                    vseqs.append(tuple(vseq))
                    elens.append(np.sum([lengths[tuple(vseq[k:k+2])]
                                         for k in range(len(vseq) - 1)]))
                    c = Counter([tags[tuple(vseq[k:k+2])]
                                 for k in range(len(vseq) - 1)])
                    etags.append(c.most_common(1)[0][0])
                    history.add((q, p))
                    new_leaves.add(q)
                visited.add(o)
                self.setProgress(len(visited)/COUNT*100)
            leaves = new_leaves.difference(visited)
            if len(leaves) == 0 and len(nodes) > len(visited):
                leaves = {min(nodes.difference(visited))}
        G.vseqs = dict(zip(edges, vseqs))
        i, j = np.stack(edges, axis=1)
        G.edges = pd.DataFrame({'i': i, 'j': j, 'length': elens, 'tags': etags})
        print(f' - {len(G.edges):,} edges')
        
        return True
    
    def finished(self, success: bool):
        if not success:
            print('Error')
    
    @classmethod
    def get_next_ident(cls):
        return '_'.join([cls.__name__, str(cls.ident)])


class Visualize(QgsTask):
    
    def __init__(self, G: Digraph):
        super().__init__('Visualizing model')
        self.G = G
    
    def run(self) -> bool:
        G = self.G
        
        # Nodes
        vl_nodes = QgsVectorLayer(
            f'point?crs=epsg:{G.crs}', 'nodes', 'memory')
        feats = []
        ii, COUNT = 0, G.node_count
        for (x, y) in G.nodes.to_numpy():
            f = QgsVectorLayerUtils.createFeature(
                vl_nodes, QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            feats.append(f)
            ii += 1
            self.setProgress(ii/COUNT*49)
        vl_nodes.dataProvider().addFeatures(feats)
        self.setProgress(50)
        self.vl_nodes = vl_nodes
        
        # Edges
        vl_edges = QgsVectorLayer(
            f'linestring?crs=epsg:{G.crs}', 'edges', 'memory')
        feats = []
        ii, COUNT = 0, G.edge_count
        for (i, j) in G.edges[['i', 'j']].to_numpy():
            _, vcoords = G.vseq(i, j, return_coords=True)
            f = QgsVectorLayerUtils.createFeature(
                vl_edges,
                QgsGeometry.fromPolylineXY([QgsPointXY(*p) for p in vcoords]))
            feats.append(f)
            ii += 1
            self.setProgress(50 + ii/COUNT*49)
        vl_edges.dataProvider().addFeatures(feats)
        self.setProgress(100)
        self.vl_edges = vl_edges
        
        return True
    
    def finished(self, success: bool):
        QgsProject.instance().addMapLayer(self.vl_edges)
        QgsProject.instance().addMapLayer(self.vl_nodes)
