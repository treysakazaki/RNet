
from collections import defaultdict
import numpy as np
import pandas as pd


def filter_connections(connections, action, tags):
    '''
    Filters connections based on their tag.
    
    Parameters:
        connections (pandas.DataFrame): Frame containing connection data.
        action ('include' or 'exclude'): Whether to include or exclude the
            specified tags.
        tags (List[str]): List of tags to include or exclude.
    
    Returns:
        pandas.DataFrame: `connections` frame with specified tags included or
        excluded.
    '''
    if action == 'include':
        mask = np.isin(connections['tag'].to_numpy(), tags)
    elif action == 'exclude':
        mask = np.invert(np.isin(connections['tag'].to_numpy(), tags))
    return connections.loc[mask]


def clean_points(points, connections):
    '''
    Removes points that are not used in any connections.
    
    Parameters:
        points (pandas.DataFrame): Frame containing points with unique indices.
        connections (pandas.DataFrame): Frame containing connections,
            :math:`(i, j)`, with indices corresponding to those in `points`.
    
    Returns:
        pandas.DataFrame: `points` frame excluding unused points.
    '''
    mask = np.isin(
        points.index,
        np.unique(connections.index.to_frame().to_numpy().flatten()))
    return points.loc[mask]


def reindex_points(points, connections, start=0):
    '''
    Resets indices of points to a consecutive range.
    
    Parameters:
        points (pandas.DataFrame): Frame containing points with unique indices.
        connections (pandas.DataFrame): Frame containing connections,
            :math:`(i, j)`, with indices corresponding to those in `points`.
        start (:obj:`int`, optional): Starting index. Default: 0.
    
    Returns:
        Tuple[pandas.DataFrame, pandas.DataFrame]: 2-tuple containing `points`
        and `connections` frames with new point indices.
    '''
    # Assign new indices
    points = points.reset_index()
    points.index += start
    mapping = {old: new for new, old in enumerate(points['index'])}
    points = points.drop(columns='index')
    
    # Update (i, j) indices
    ij = np.array([
        mapping[i] for i in connections.index.to_frame().to_numpy().flatten()
        ]).reshape(-1,2)
    ij += start
    connections.index = pd.MultiIndex.from_arrays(ij.T, names=['i', 'j'])
    
    return points, connections


def compute_lengths(vertices, links, dims):
    '''
    Computes the length of each link and inserts or updates the 'length' column.
    
    Parameters:
        vertices (pandas.DataFrame): Frame containing vertex data.
        links (pandas.DataFrame): Frame containing link data.
        dims (int): 2 or 3. If 2, then `vertices` must contain the columns 'x'
            and 'y'. If 3, then `vertices` must also contain the column `z`.
    
    Returns:
        pandas.DataFrame: `links` frame with 'length' column inserted or
        updated.
    '''
    ijpairs = links.index.to_frame().to_numpy()
    if dims == 2:
        cols = ['x', 'y']
        c = vertices[cols].loc[ijpairs.flatten()].to_numpy().reshape(-1,4)
        d = np.column_stack([c[:,2]-c[:,0], c[:,3]-c[:,1]])
    elif dims == 3:
        cols = ['x', 'y', 'z']
        c = vertices[cols].loc[ijpairs.flatten()].to_numpy().reshape(-1,6)
        d = np.column_stack([c[:,3]-c[:,0], c[:,4]-c[:,1], c[:,5]-c[:,2]])
    links['length'] = np.linalg.norm(d, axis=1)
    return links


def get_neighbors(connections, directed):
    '''
    Returns dictionary mapping point ID to set of neighboring point IDs.
    
    Parameters:
        connections (pandas.DataFrame): Frame containing connections.
        directed (bool): If True, then :math:`(i, j)` pairs in are interpreted
            as ordered pairs.
    
    Returns:
        Dict[int, Set[int]]: Mapping from point ID to set of neighboring point
        IDs.
    '''
    neighbors = defaultdict(set)
    if directed:
        for (i, j) in connections.index.to_list():
            neighbors[i].add(j)
    else:
        for (i, j) in connections.index.to_list():
            neighbors[i].add(j)
            neighbors[j].add(i)
    return dict(neighbors)


def extract_nodes(vertices, links, directed):
    '''
    Extracts nodes from a set of vertices. Nodes are the subset of vertices
    that have exactly one or more than two neighbors.
    
    Parameters:
        vertices (pandas.DataFrame): Frame containing vertex data.
        links (pandas.DataFrame): Frame containing link data.
        directed (bool): If True, then :math:`(i, j)` pairs in the links frame
            are interpreted as ordered pairs.
    
    Returns:
        pandas.DataFrame: `vertices` frame containing only the points with
        exactly one or more than two neighbors.
    '''
    neighbors = get_neighbors(links, directed)
    nodes = set(i for i, n in neighbors.items() if len(n) != 2)
    mask = np.isin(vertices.index, list(nodes), assume_unique=True)
    return vertices.loc[mask]


def extract_edges(links, nodes, directed):
    '''
    Extracts edges from a set of links. Edges are constructed by chaining one
    or more links together such that the endpoints are both nodes.
    
    Parameters:
        links (pandas.DataFrame): Frame containing edge data.
        nodes (pandas.DataFrame): Frame containing node data.
        directed (bool): If True, then :math:`(i, j)` pairs in the links frame
            are interpreted as ordered pairs. The resulting set of edges will
            also be directed.
    
    Returns:
        pandas.DataFrame: Frame containing edge data.
    '''
    neighbors = get_neighbors(links, directed)
    nodes = set(nodes.index)
    
    ijpairs = []
    records = []
    
    history = set()
    unvisited = nodes.copy()
    
    while True:
        try:
            leaves = {unvisited.pop()}
        except KeyError:
            break
        else:
            while len(leaves) > 0:
                new_leaves = set()
                for o in leaves:
                    for n in neighbors[o]:
                        if (o, n) in history:
                            continue
                        vseq = [o, n]
                        p, q = o, n
                        while q not in nodes:
                            x = neighbors[q].difference({p}).pop()
                            vseq.append(x)
                            p, q = q, x
                        i, j = vseq[0], vseq[-1]
                        new_leaves.add(j)
                        history.add((q, p))
                        if i > j:
                            i, j = j, i
                            vseq.reverse()
                        ijpairs.append((i, j))
                        records.append((tuple(vseq), ))
                unvisited.difference_update(leaves)
                leaves = new_leaves.intersection(unvisited)
    
    index = pd.MultiIndex.from_tuples(ijpairs, names=['i', 'j'])
    return pd.DataFrame.from_records(records, index=index, columns=['vseq'])


def concatenate(*frames):
    '''
    Parameters:
        *frames (Tuple[pandas.DataFrame, pandas.DataFrame]): Frames containing
            points and connections data.
    '''
    points = []
    connections = []
    tags = []
    PCOUNT = 0
    for dfpoints, dfconnections in frames:
        coords = dfpoints.values.tolist()
        ijpairs = dfconnections.index.to_frame().to_numpy()
        ijpairs += PCOUNT
        ijpairs = ijpairs.tolist()
        points.extend(coords)
        connections.extend(ijpairs)
        tags.extend(dfconnections.values.tolist())
        PCOUNT += len(coords)
    points = pd.DataFrame.from_records(points, columns=['x', 'y'])
    connections = pd.DataFrame.from_records(
        tags, index=pd.MultiIndex.from_tuples(connections, names=['i', 'j']),
        columns=['tag'])
    return points, connections
