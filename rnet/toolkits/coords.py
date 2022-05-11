import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
try:
    from osgeo import osr
except:
    pass


def get_crs_info(crs):
    '''
    Return information about a CRS.
    
    Parameters:
        crs (int): EPSG code.
    
    Returns:
        Dict[str, Any]: Dictionary mapping descriptor to value.
    '''
    ref = osr.SpatialReference()
    err = ref.ImportFromEPSG(crs)
    if err > 0:
        return
    else:
        area = ref.GetAreaOfUse()
        lonmin, lonmax = area.west_lon_degree, area.east_lon_degree
        latmin, latmax = area.south_lat_degree, area.north_lat_degree
        if ref.IsGeographic():
            reftype = 'geographic'
            units = ref.GetAngularUnitsName()
            xmin, xmax = lonmin, lonmax
            ymin, ymax = latmin, latmax
        elif ref.IsProjected():
            reftype = 'projected'
            units = ref.GetLinearUnitsName()
            (xmin,ymin), (xmax,ymax) = transform2d(
                np.array([(lonmin,latmin), (lonmax,latmax)]), 4326, crs)
        return {'EPSG': crs,
                'name': ref.GetName(),
                'type': reftype,
                'units': units,
                'lonmin': lonmin,
                'lonmax': lonmax,
                'latmin': latmin,
                'latmax': latmax,
                'xmin': xmin,
                'xmax': xmax,
                'ymin': ymin,
                'ymax': ymax}


def concatenate_points(*frames):
    '''
    Concatenate frames containing point coordinates.
    
    Parameters:
        *frames (pandas.DataFrame): Frames containing point coordinates.
    
    Returns:
        pandas.DataFrame: Concatenated frame.
    '''
    points = []
    for df in frames:
        points.extend(df.values.tolist())
    df = pd.DataFrame.from_records(points, columns=['x', 'y', 'z'])
    return df


def create_tree(points):
    '''
    Return two-dimensional :math:`k`-d tree for quick nearest-neighbor query.
    
    Parameters:
        points (:obj:`numpy.ndarray`, shape(N,2)): The N points at which
            to compute elevations.
    
    Returns:
        scipy.spatial.cKDTree:
    '''
    return cKDTree(points)


def get_bounds2d(coords):
    '''
    Return coordinate bounds.
    
    Parameters:
        coords (:obj:`numpy.ndarray`, shape(N,2)): Coordinates.
    
    Returns:
        Tuple[float]: 4-tuple containing ``xmin``, ``ymin``, ``xmax, ``ymax``.
    '''
    xmin, ymin = np.min(coords, axis=0)
    xmax, ymax = np.max(coords, axis=0)
    return (xmin, ymin, xmax, ymax)


def get_bounds3d(coords):
    '''
    Return coordinate bounds.
    
    Parameters:
        coords (:obj:`numpy.ndarray`, shape(N,3)): Coordinates.
    
    Returns:
        Tuple[float]: 6-tuple containing ``xmin``, ``ymin``, ``zmin``, ``xmax``,
            ``ymax``, ``zmax``.
    '''
    xmin, ymin, zmin = np.min(coords, axis=0)
    xmax, ymax, zmax = np.max(coords, axis=0)
    return (xmin, ymin, zmin, xmax, ymax, zmax)


def get_elev(data, tree, x, y, r, p):
    '''
    Return elevation at a single point. The elevation is computed via
    inverse distance weighting (IDW) interpolation.
    
    Parameters:
        data (pandas.DataFrame): Elevation data.
        tree (scipy.spatial.cKDTree): :math:`k`-d tree for nearest-neighbor
            query.
        x (float): `x`-coordinate.
        y (float): `y`-coordinate.
        r (float): Radius for neighbor search.
        p (int): Power setting for IDW interpolation.
    
    Returns:
        float:
    '''
    ngbrs = tree.query_ball_point((x, y), r)
    xyz = data.iloc[ngbrs].to_numpy()
    d = np.power(np.linalg.norm(xyz[:,0:2] - np.array([x, y]), axis=1), p)
    z = xyz[:,2]
    return np.sum(z/d) / np.sum(1/d)


def get_elevs(data, tree, points, r, p):
    '''
    Return elevations at multiple points. The elevations are computed via
    inverse distance weighting (IDW) interpolation.
    
    Parameters:
        data (pandas.DataFrame): Elevation data.
        tree (scipy.spatial.cKDTree): :math:`k`-d tree for nearest-neighbor
            query.
        points (:obj:`numpy.ndarray`, shape(N,2)): The N points at which
            to compute elevations.
        r (float): Radius for neighbor search.
        p (int): Power setting for IDW interpolation.
    
    Returns:
        List[float]:
    '''
    neighbors = cKDTree(points).query_ball_tree(tree, r)
    coords = data.to_numpy()
    res = []
    for k in np.arange(len(points)):
        xyz = coords[neighbors[k]]
        d = np.power(np.linalg.norm(xyz[:,0:2] - points[k], axis=1), p)
        z = xyz[:,2]
        res.append(np.sum(z/d) / np.sum(1/d))
    return res


def transform2d(coords, source, destination):
    '''
    Transform two-dimensional coordinates from `source` to `destination` CRS.
    
    Parameters:
        coords (:obj:`numpy.ndarray`, shape(N,2)): Coordinates to transform.
        source (int): EPSG code of source CRS.
        destination (int): EPSG code of destination CRS.
    
    Returns:
        :obj:`numpy.ndarray`, shape(N,2): Transformed coordinates.
    '''
    src = osr.SpatialReference()
    src.ImportFromEPSG(source)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(destination)
    ct = osr.CoordinateTransformation(src, dst)
    transformed = np.array(ct.TransformPoints(coords[:,[1,0]]))
    return transformed[:,[1,0]]
