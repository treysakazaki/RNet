from typing import List, Set, Tuple, Union
import numpy as np
import pandas as pd


class Graph:
    
    def __init__(self):
        super().__init__()
    
    def actions(self, i: int) -> Set[Tuple[int, int]]:
        '''
        Returns set of edges that originate at node i.
        
        Parameters:
            i (int) -- node ID
        
        Return type:
            Set[Tuple[int, int]]
        '''
        return {(i, n) for n in self.neighbors(i)}
    
    def edge_id(self, i: int, j: int):
        '''
        Returns ID of edge (i, j).
        
        Parameters:
            i (int) -- node ID
            j (int) -- node ID
        '''
        try:
            if i > j:
                i, j = j, i
            return self.edges.loc[lambda df: df['i'] == i] \
                             .loc[lambda df: df['j'] == j] \
                             .iloc[0].name
        except IndexError:
            return
    
    def length(self, i: int, j: int):
        '''
        Returns length of edge (i, j). IndexError is raised if edge doesn't
        exist.
        '''
        if i > j:
            i, j = j, i
        return self.edges.loc[lambda df: df['i'] == i] \
                         .loc[lambda df: df['j'] == j] \
                         .iloc[0]['length']
    
    def ncoords(self, i: Union[int, List[int]]):
        '''
        Returns (x, y) coordinates of a node or list of nodes.
        
        Parameters:
            i (Union[int, List[int]]) -- node ID or list of node IDs
        
        Return type:
            Tuple[float, float] or List[Tuple[float, float]]
        '''
        if isinstance(i, (int, np.integer)):
            return tuple(self.nodes.loc[i].to_numpy())
        elif type(i) is list:
            return [tuple(x) for x in self.nodes.loc[i].to_numpy()]
    
    def ndist(self, i: int, j: int):
        '''
        Returns 2D Euclidean distance between nodes i and j.
        
        Paramters:
            i (int) -- node ID
            j (int) -- node ID
        '''
        return np.linalg.norm(
            np.diff(self.nodes.loc[[i, j]].to_numpy(), axis=0))
    
    def neighbors(self, i: int) -> Set[int]:
        '''
        Returns set of nodes adjacent to node i.
        
        Paramters:
            i (int) -- node ID
        
        Return type:
            Set[int]
        '''
        s = set(self.edges.loc[lambda df: df['i'] == i]['j'])
        s.update(self.edges.loc[lambda df: df['j'] == i]['i'])
        return s
    
    def random_node(self):
        '''
        Returns a randomly chosen node.
        '''
        return np.random.choice(self.nodes.index)
    
    def random_nodes(self, N: int, replace: bool = True, **kwargs):
        '''
        Returns N randomly chosen nodes with/without replacement.
        
        Parameters:
            N (int = None) -- number of nodes to choose
            replace (bool = True) -- whether to sample with replacement
        
        Keyword arguments:
            r (float) -- maximum distance between consecutive nodes
        '''
        if 'r' in kwargs:
            r = kwargs['r']
            route = [self.random_node()]
            for _ in np.arange(N - 1):
                x, y = self.ncoords(route[-1])
                df = self.reduced_nodes(xyr=(x, y, r))
                route.append(np.random.choice(df.index))
            return np.array(route)
        else:
            return np.random.choice(self.nodes.index, N, replace)
    
    def reduce(self, **kwargs):
        '''
        Reduces the model in-place based on given parameters.
        
        Keyword arguments:
            xmin (Union[int, float]) -- lower bound on x-coordinate
            ymin (Union[int, float]) -- lower bound on y-coordinate
            xmax (Union[int, float]) -- upper bound on x-coordinate
            ymax (Union[int, float]) -- upper bound on y-coordinate
            xyr (Tuple[float, float, float]) -- for circle centered at (x, y)
                with radius r
        '''
        self.nodes = self.reduced_nodes(**kwargs)
        self.nodesUpdated.emit(self.node_count)
        self.edges = self.edges.loc[
            lambda df: (df['i'].isin(self.node_ids)) \
                     & (df['j'].isin(self.node_ids))]
        self.edgesUpdated.emit(self.edge_count)
    
    def reduced_nodes(self, **kwargs):
        '''
        Returns reduced nodes based on given parameters.
        
        Keyword arguments:
            xmin (Union[int, float]) -- lower bound on x-coordinate
            ymin (Union[int, float]) -- lower bound on y-coordinate
            xmax (Union[int, float]) -- upper bound on x-coordinate
            ymax (Union[int, float]) -- upper bound on y-coordinate
            xyr (Tuple[float, float, float]) -- for circle centered at (x, y)
                with radius r
        
        Return type:
            pandas.DataFrame
        '''
        res = self.nodes.copy()
        if 'xmin' in kwargs:
            res = res.loc[lambda df: kwargs['xmin'] <= df['x']]
        if 'ymin' in kwargs:
            res = res.loc[lambda df: kwargs['ymin'] <= df['x']]
        if 'xmax' in kwargs:
            res = res.loc[lambda df: df['x'] <= kwargs['xmax']]
        if 'ymax' in kwargs:
            res = res.loc[lambda df: df['y'] <= kwargs['ymax']]
        if 'xyr' in kwargs:
            x, y, r = kwargs['xyr']
            res = res.loc[lambda df: np.linalg.norm(
                df[['x', 'y']].to_numpy() - np.array([x, y]), axis=1) < r]
        return res
    
    def set_edges(self, path_to_csv: str):
        self.edges = pd.read_csv(path_to_csv, index_col='fid',
                                 usecols=['fid', 'i', 'j', 'length'])
        self.vseqs = pd.read_csv(path_to_csv, index_col='fid',
                                 usecols=['fid', 'vseq'])
    
    def set_nodes(self, path_to_csv: str):
        self.nodes = pd.read_csv(path_to_csv, index_col='fid',
                                 usecols=['fid', 'x', 'y'])
    
    def set_vertices(self, path_to_csv: str):
        self.vertices = pd.read_csv(path_to_csv, index_col='fid',
                                    usecols=['fid', 'x', 'y'])
    
    def vcoords(self, i: Union[int, List[int]]):
        '''
        Returns (x, y) coordinates of a vertex or list of vertices.
        
        Parameters:
            i (Union[int, List[int]]) -- vertex ID or list of vertex IDs
        
        Return type:
            Tuple[float, float] or List[Tuple[float, float]]
        '''
        if isinstance(i, (int, np.integer)):
            return tuple(self.vertices.loc[i].to_numpy())
        elif type(i) is list:
            return [tuple(x) for x in self.vertices.loc[i].to_numpy()]
    
    def vdist(self, i: int, j: int) -> float:
        '''
        Returns 2D Euclidean distance between vertices i and j.
        
        Paramters:
            i (int) -- vertex ID
            j (int) -- vertex ID
        '''
        return np.linalg.norm(
            np.diff(self.vertices.loc[[i, j]].to_numpy(), axis=0))
    
    def vseq(self, *args):
        '''
        Returns vertex sequence associated with edge.
        
        vseq(self, i: int, j: int) -- returns vertex sequence of edge (i, j)
        vseq(self, k: int) -- returns vertex sequence of edge k
        '''
        if len(args) == 1:
            s = self.vseqs.loc[args[0]]['vseq']
            return tuple(int(x) for x in s[1:-1].split(', '))
        elif len(args) == 2:
            i, j = args
            s = self.vseqs.loc[self.edge_id(i, j)]['vseq']
            vseq = tuple(int(x) for x in s[1:-1].split(', '))
            if i < j:
                return vseq
            else:
                return tuple(reversed(vseq))
    
    @property
    def edge_count(self):
        return len(self.edges)
    
    @property
    def edge_pairs(self):
        f = set(zip(self.edges['i'], self.edges['j']))
        b = set(t[::-1] for t in f)
        return f.union(b)
    
    @property
    def node_count(self):
        return len(self.nodes)
    
    @property
    def node_ids(self):
        return set(self.nodes.index)
    
    @property
    def vertex_count(self):
        return len(self.vertices)
    
    @property
    def xmax(self):
        return max(self.nodes['x'], default=None)
    
    @property
    def xmin(self):
        return min(self.nodes['x'], default=None)
    
    @property
    def ymax(self):
        return max(self.nodes['y'], default=None)
    
    @property
    def ymin(self):
        return min(self.nodes['y'], default=None)
