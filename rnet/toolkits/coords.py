
import numpy as np
from osgeo import osr


def transform_coords2d(coords, srccrs, dstcrs):
    '''
    Transforms two-dimensional coordinates.
    
    Parameters:
        coords (:obj:`numpy.ndarray`, shape(N,2)): Coordinates to transform.
        srccrs (int): EPSG code of source CRS.
        dstcrs (int): EPSG code of destination CRS.
    
    Returns:
        :obj:`numpy.ndarray`, shape(N,2): Transformed coordinates.
    '''
    src = osr.SpatialReference()
    src.ImportFromEPSG(srccrs)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(dstcrs)
    ct = osr.CoordinateTransformation(src, dst)
    transformed = np.array(ct.TransformPoints(coords[:,[1,0]]))
    return transformed[:,[1,0]]

