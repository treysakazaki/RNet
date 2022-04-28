
import numpy as np
from osgeo import gdal
import pandas as pd


def from_tif(path_to_tif):
    '''
    Loads elevation data from a TIF file.
    
    Parameters:
        path_to_osm (str): Path to OSM file.
    
    Returns:
        pandas.DataFrame: Frame containing elevation data.
    '''
    # Read source file
    resource = gdal.Open(path_to_tif)
    transform = resource.GetGeoTransform()
    x0, y0 = transform[0], transform[3]
    dx, dy = transform[1], transform[5]
    
    # Extract elevations
    band = resource.GetRasterBand(1).ReadAsArray()
    h, w = band.shape
    x = np.tile(np.arange(x0, x0+w*dx, dx), h)
    y = np.concatenate([np.full(w,y0+j*dy) for j in np.arange(h)])
    z = band.flatten()
    
    # Construct frame
    df = pd.DataFrame(np.column_stack([x,y,z]), columns=['x','y','z'])
    return df
