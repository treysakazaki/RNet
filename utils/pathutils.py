from collections import Counter
from typing import List, Union

import matplotlib.pyplot as plt
import numpy as np

from rnet.core.model import Graph


class Path:
    
    model: Graph = None
    
    def __init__(self, nseq: List[int]):
        self.nseq = nseq
        PathUtils.validate(self, self.model)
    
    def plotXY(self, show_nodes: bool = True, show_vertices: bool = False,
             show_points: bool = False, **point_params):
        PathUtils.plotXY(self, show_nodes, show_vertices, show_points,
                         **point_params)
    
    def pseq(self, **kwargs):
        '''
        Returns point sequence. One of the following methods can be specified
        by the 'method' keyword argument.
        
        Method 1:
            Points are spaced by exactly d (m) along links until the next
            vertex is reached. Nodes and vertices are retained.
        Method 2:
            Points are equally spaced along links such that the maximum
            interval between consecutive points does not exceed d (m). Nodes
            and vertices are retained.
        Method 3 (default): 
            Points are spaced along the path at fixed interval, d (m). Nodes
            and vertices are not retained.
        
        Keyword arguments:
            d (int = 50) -- maximum interval between points in meters (optional)
            method (int = 3) -- 1, 2, or 3 (optional)
            returntype (str = 'py') -- 'py' or 'np' (optional)
        '''
        d = kwargs.get('d', 50)
        method = kwargs.get('method', 3)
        returntype = kwargs.get('returntype', 'py')
        
        vcoords = np.array(self.vcoords)
        pseq = np.array([vcoords[0]])
        
        if method == 1:
            for k in range(1, len(vcoords)):
                pseq = np.append(pseq, [vcoords[k]], axis=0)
                dx, dy = pseq[-1] - pseq[-2]
                s = np.linalg.norm([dx, dy])  # distance to next vertex
                t = np.arctan2(dy, dx)  # heading
                pseq = np.insert(pseq, -1, pseq[-2] + np.stack(
                    np.arange(1, int(s//d) + 1) * d * np.vstack(
                        [np.cos(t), np.sin(t)]), axis=1), axis=0)
        if method == 2:
            for k in range(1, len(vcoords)):
                pseq = np.append(pseq, [vcoords[k]], axis=0)
                dx, dy = pseq[-1] - pseq[-2]
                s = np.linalg.norm([dx, dy])  # distance to next vertex
                if s <= d:
                    continue
                else:
                    N = s // d  # number of points to add
                    r = s / (N+1)  # interval between points
                    t = np.arctan2(dy, dx)  # heading
                    pseq = np.insert(pseq, -1, pseq[-2] + np.stack(
                        np.arange(1, N + 1) * r * np.vstack(
                            [np.cos(t), np.sin(t)]), axis=1), axis=0)
        if method == 3:
            dists = np.array([np.linalg.norm(vcoords[k+1] - vcoords[k])
                              for k in range(len(vcoords) - 1)])
            cdists = np.concatenate([[0], np.cumsum(dists)])
            indices = np.searchsorted(cdists, np.arange(d, cdists[-1], d))
            for k in range(len(indices)):
                i = indices[k]
                r = d * (k + 1) - cdists[i-1]
                dx, dy = vcoords[i] - vcoords[i-1]
                t = np.arctan2(dy, dx)
                pseq = np.append(
                    pseq, [vcoords[i-1] + r*np.array([np.cos(t), np.sin(t)])],
                    axis=0)
        else:
            raise ValueError
        
        if returntype == 'np':
            return pseq
        elif returntype == 'py':
            return [tuple(x) for x in pseq]

    def ntimes(self, spd: Union[float, List[float]], units: str = 'kph'
              ) -> List[float]:
        '''
        Returns arrival time at each node in path.

        Parameters:
            spd (Union[float, List[float]]) -- fixed speed travelled along path
                or average speed along each edge in path
            units (str) -- 'kph' or 'mps'
        
        Return type:
            List[float]
        '''
        if units == 'kph':
            spd = spd * 1000 / 3600
        elif units == 'mps':
            pass
        else:
            raise ValueError
        times = np.array(self.lengths) / spd
        return np.cumsum(times)

    @classmethod
    def set_model(cls, model: Graph):
        cls.model = model
    
    @property
    def edges(self):
        '''Corresponding edge sequence.'''
        return [tuple(self.nseq[k:k+2]) for k in range(len(self.nseq) - 1)]
    
    @property
    def edge_counts(self):
        '''Occurences of each edge in path.'''
        return Counter(self.edges)
    
    @property
    def G(self):
        '''Goal node.'''
        return self.nseq[-1]
    
    @property
    def length(self) -> float:
        '''Total length of path.'''
        return np.sum(self.lengths)
    
    @property
    def lengths(self) -> List[float]:
        '''Lengths of each edge along path.'''
        return [self.model.length(i, j) for (i, j) in self.edges]
    
    @property
    def N(self):
        '''Number of nodes in path, including S and G.'''
        return len(self.nseq)
    
    @property
    def ncoords(self):
        return self.model.ncoords(self.nseq)
    
    @property
    def S(self):
        '''Start node.'''
        return self.nseq[0]
    
    @property
    def vcoords(self):
        '''Coordinates of each vertex along path.'''
        return self.model.vcoords(self.vseq)
    
    @property
    def vseq(self):
        '''Corresponding vertex sequence.'''
        vseq = [self.S]
        for k in range(len(self.nseq) - 1):
            vseq.extend(self.model.vseq(*self.nseq[k:k+2])[1:])
        return vseq


class PathUtils:
    
    @staticmethod
    def plotXY(path: Path, show_nodes: bool = True, show_vertices: bool = False,
               show_points: bool = False, fign: int = 1, c='k', **point_params):
        plt.figure(fign)
        plt.plot(*np.stack(path.vcoords, axis=1), c=c, zorder=0)
        if show_points:
            plt.scatter(*np.stack(path.pseq(**point_params), axis=1),
                        s=25, c='w', edgecolors='k', zorder=1)
        if show_vertices:
            plt.scatter(*np.stack(path.vcoords, axis=1),
                        s=25, c='#d5d5d5', edgecolors='k', zorder=2)
        if show_nodes:
            plt.scatter(*np.stack(path.ncoords, axis=1),
                        s=25, c='#a2d418', edgecolors='k', zorder=3)
        plt.draw()
        plt.xlabel('X (m)')
        plt.ylabel('Y (m)')
        plt.axis('equal')
        plt.tick_params(direction='in', top=True, right=True)
        plt.tight_layout()
        plt.show()

    @staticmethod
    def validate(path: Path, model: Graph):
        invalid_edges = set(path.edges).difference(model.edge_pairs)
        if invalid_edges:
            return False
        else:
            return True
