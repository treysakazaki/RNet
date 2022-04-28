
import numpy as np
import pandas as pd


def filter_connections(connections, **kwargs):
    '''
    Filters connections based on their tag.
    
    Keyword arguments:
        include (:obj:`List[str]`, optional): List of tags to include.
        exclude (:obj:`List[str]`, optional): List of tags to exclude.
    
    Returns:
        pandas.DataFrame: `connections` frame reduced based on `include` or
        `exclude` parameter.
    
    Raises:
        KeyError: If an incorrect keyword argument is given.
        TypeError: If an incorrect number of keyword arguments is given.
    '''
    if len(kwargs) == 1:
        tags = connections['tag'].to_numpy()
        if 'include' in kwargs:
            mask = np.isin(tags, kwargs['include'])
        elif 'exclude' in kwargs:
            mask = np.invert(np.isin(tags, kwargs['exclude']))
        else:
            raise KeyError("expected keyword 'include' or 'exclude'")
        return connections.loc[mask]
    else:
        raise TypeError("expected keyword 'include' or 'exclude'")


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

