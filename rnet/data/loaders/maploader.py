
import numpy as np
from osgeo import ogr
import pandas as pd


def from_osm(path_to_osm):
    '''
    Loads map data from an OSM file.
    
    Parameters:
        path_to_osm (str): Path to OSM file.
    
    Returns:
        Tuple[pandas.DataFrame, pandas.DataFrame]: Frames containing vertex
        and link data.
    '''
    # Read source file
    osm_driver = ogr.GetDriverByName('OSM')
    data_source = osm_driver.Open(path_to_osm, 0)
    layer = data_source.GetLayer('lines')
    
    # Extract vertices
    roads = [feature.GetGeometryRef().GetPoints() for feature in layer]
    coords, inv = np.unique(np.concatenate(roads), return_inverse=True, axis=0)
    
    # Extract links
    num_points = [len(road) for road in roads]
    indices = np.cumsum([0] + num_points)
    ijpairs = np.array([(i, i+1) for k in range(len(indices) - 1)
                        for i in np.arange(indices[k], indices[k+1] - 1)])
    ijpairs = np.sort(inv[ijpairs.flatten()].reshape(-1, 2))
    tags = np.concatenate([np.full(num_points[k] - 1, feat.GetField('highway'))
                           for k, feat in enumerate(layer)])
    
    # Construct frames
    vertices = pd.DataFrame(coords, columns=['lon', 'lat'])
    links = pd.DataFrame(
        tags, index=pd.MultiIndex.from_arrays(ijpairs.T, names=['i', 'j']),
        columns=['tag'])
    return vertices, links


def from_csvs(path_to_vertices, path_to_links):
    '''
    Loads map data from a pair of CSV files containing vertex and link data.
    
    Parameters:
        path_to_vertices (str): Path to CSV file containing vertex data.
        path_to_links (str): Path to CSV file containing link data.
    
    Returns:
        Tuple[pandas.DataFrame, pandas.DataFrame]: Frames containing vertex
        and link data.
    '''
    vertices = pd.read_csv(path_to_vertices, index_col=0)
    links = pd.read_csv(path_to_links, index_col=[0,1])
    return vertices, links
