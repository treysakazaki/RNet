from collections import Counter
import signal
import time

import numpy as np

from rnet.core.model import Graph
from rnet.utils.pathutils import Path


class AStar:
    '''
    A-star algorithm.
    '''
    
    def __init__(self, model: Graph):
        self.model = model
        self.initialize_tables()
    
    def construct(self, S: int, G: int):
        if S == G:
            self.history.update({(S, G): [S, G]})
            return [S, G]
        o = self.origins.get(S)
        path = [G]
        while path[0] != S:
            path.insert(0, o[path[0]])
        self.history.update({(S, G): path})
        return path

    def initialize_tables(self):
        self.origins = dict()
        self.distances = dict()
        self.scores = dict()
        self.history = dict()
    
    def shortest_path(self, S: int, G: int, verbose: bool = False):
        if verbose: start = time.time()
        if (S, G) in self.history:
            if verbose: print(f'Comp. time: {time.time()-start:,.4f} s')
            return self.history[(S, G)]
        else:
            self.update_tables(S, G)
            res = self.construct(S, G)
            if verbose: print(f'Comp. time: {time.time()-start:,.4f} s')
            return res
    
    def update_tables(self, S: int, G: int):
        # Retrieve origin and distance maps if they exist, else initialize
        o = self.origins.setdefault(
            S, {n: None for n in self.model.node_ids if n != S})
        d = self.distances.setdefault(
            S, {n: (np.inf if n != S else 0) for n in self.model.node_ids})
        f = self.scores.setdefault(
            S, {n: (np.inf if n != S else self.model.ndist(S, G))
                for n in self.model.node_ids})
        # Update tables
        while G in d:
            x = list(f.keys())[np.argmin(list(f.values()))]
            if x == G:
                break
            d_to_x = d.pop(x)
            f.pop(x)
            for n in self.model.neighbors(x).intersection(d):
                old = d[n]
                new = d_to_x + self.model.length(x, n)
                if new < old:
                    o.update({n: x})
                    d.update({n: new})
                    f.update({n: new + self.model.ndist(n, G)})


class BFS:
    '''
    Best-first search.
    '''
    
    def __init__(self, model: Graph):
        self.model = model
    
    def shortest_path(self, S: int, G: int, verbose: bool = False):
        '''
        Finds a path from node S to node G. Then, cycles are pruned.
        
        Parameters:
            S (int) -- start node ID
            G (int) -- goal node ID
            verbose (bool = False) -- for debugging
        '''
        # Find path
        path = [S]
        edges = set()
        x = S
        while x != G:
            try:
                cands = list(self.model.actions(x).difference(edges))
                assert len(cands) > 0
            except AssertionError:
                while len(cands) == 0:
                    x = path.pop(-1)
                    if verbose: print(f'Removed {x}')
                    x = path[-1]
                    cands = list(self.model.actions(x).difference(edges))
            finally:
                dists = list(map(self.model.ndist,
                                 np.stack(cands, axis=1)[1], [G]*len(cands)))
                best_cand = cands[np.argmin(dists)]
                if verbose:
                    print(x)
                    print(*np.stack(list(zip(cands, dists))), sep='\n')
                    print(best_cand)
                edges.add(best_cand)
                x = best_cand[1]
                path.append(x)
                if verbose: print(f'Appended {x}')
        # Pruning
        n, c = Counter(path).most_common(1)[0]
        while c > 1:
            i = path.index(n)
            j = list(reversed(path)).index(n)
            if verbose: print(f'Removing cycle {path[i:-j]}')
            path = path[:i+1] + path[-j:]
            n, c = Counter(path).most_common(1)[0]
        return path
    

class Dijkstra:
    '''
    Dijkstra's algorithm.
    '''
    
    def __init__(self, model: Graph):
        self.model = model
        self.initialize_tables()
    
    def construct(self, S: int, G: int):
        if S == G:
            self.history.update({(S, G): [S, G]})
            return [S, G]
        o = self.origins.get(S)
        path = [G]
        while path[0] != S:
            path.insert(0, o[path[0]])
        self.history.update({(S, G): path})
        return path
    
    def initialize_tables(self):
        self.origins = dict()
        self.distances = dict()
        self.history = dict()
    
    def shortest_path(self, S: int, G: int, verbose: bool = False):
        if verbose: start = time.time()
        if (S, G) in self.history:
            if verbose: print(f'Comp. time: {time.time()-start:,.4f} s')
            return self.history[(S, G)]
        else:
            self.update_tables(S, G)
            res = self.construct(S, G)
            if verbose: print(f'Comp. time: {time.time()-start:,.4f} s')
            return res
    
    def update_tables(self, S: int, G: int):
        # Retrieve origin and distance maps if they exist, else initialize
        o = self.origins.setdefault(
            S, {n: None for n in self.model.node_ids if n != S})
        d = self.distances.setdefault(
            S, {n: (np.inf if n != S else 0) for n in self.model.node_ids})
        # Update tables
        while G in d:
            x = list(d.keys())[np.argmin(list(d.values()))]
            if x == G:
                break
            d_to_x = d.pop(x)
            for n in self.model.neighbors(x).intersection(d):
                old = d[n]
                new = d_to_x + self.model.length(x, n)
                if new < old:
                    o.update({n: x})
                    d.update({n: new})


def handler(signum, frame):
    raise TimeoutError


def test(pairs, method, max_time=0):
    '''
    Returns list of shortest paths between each pair of start/goal nodes in
    'pairs', found using the given 'method'.

    Parameters:
        pairs (List[Tuple[int, int]]) -- pairs of start/goal nodes
        method -- instance of a subclass of ShortestPath
        max_time (int = 0) -- maximum time allotted for finding the shortest
            path between each pair; TimeoutError is raised if computation time
            exceeds max_time; infinite time is allotted if max_time is 0
    '''
    paths = []
    for i, (S, G) in enumerate(pairs):
        print(f'{i+1:>2}  {S:>6} -> {G:>6}', end=' | ')
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(max_time)
        try:
            start = time.time()
            nseq = method.shortest_path(S, G)
        except TimeoutError:
            print('Timeout')
        except KeyboardInterrupt:
            break
        else:
            path = Path(nseq)
            paths.append(path)
            print(f'cost: {path.length:9,.2f}',
                  f'comp time: {time.time()-start:6.2f} s',
                  sep=' | ')
    return paths
