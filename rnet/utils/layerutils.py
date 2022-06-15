from configparser import ConfigParser
from enum import Enum, auto
import os

from PyQt5.QtCore import QVariant

try:
    from qgis.core import (
        QgsField,
        QgsFields,
        QgsGeometry,
        QgsPointXY,
        QgsProject,
        QgsVectorFileWriter,
        QgsVectorLayer,
        QgsVectorLayerUtils
        )
except:
    pass

from rnet.exceptions import require_qgis, ConfigError


if __name__ != '__console__':
    try:
        CONFIG = ConfigParser()
        CONFIG.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    except:
        raise ConfigError


class LayerType(Enum):
    '''
    Enumeration of layer types.
    '''
    BOUNDARIES = auto()
    VERTICES = auto()
    LINKS = auto()
    NODES = auto()
    EDGES = auto()


def get_config(layer_type):
    '''
    Return configuration dictionary for given layer type.
    
    Parameters:
        layer_type (LayerType): Layer type.
    
    Returns:
        Dict[str, Any]: Dictionary containing configuration settings. Possible
        keys are the following:
        
        * **geometry** (*str*) -- {'point', 'linestring', 'polygon'}
        * **size** (*float*) -- point size, default: 1.0
        * **width** (*float*) -- line width, default: 0.5
        * **color** (*Tuple[int, int, int]*) -- render color, default: (0, 0, 0)
        * **opacity** (*float*) -- opacity in range [0, 1)
        * **maxscale** (*int* or *float*) -- maximum scale
        * **minscale** (*int* or *float*) -- minimum scale
        * **renderer** (*str*) -- {'rulebased', 'categorized'}
        * **outlinecolor** (*Tuple[int, int, int]*) -- outline color for
          polygon geometry, default: (0, 0, 0)
        * **outlinewidth** (*float*) -- outline width for polygon geometry,
          default: 0.5
    
    '''
    str2rgb = lambda s: tuple(map(int, s.split(',')))
    # Load configuration
    config = dict(CONFIG[layer_type.name])
    # Required fields
    # Optional fields
    config['color'] = str2rgb(config['color'])
    config['opacity'] = float(config['opacity'])
    config['outlinecolor'] = str2rgb(config['outlinecolor'])
    config['outlinewidth'] = float(config['outlinewidth'])
    return config


@require_qgis
def create_layer(layer_type, crs, name=None):
    '''
    Create a temporary vector layer.
    
    Parameters:
        layer_type (str): 'vertices', 'links', 'nodes', 'edges'.
        crs (int): EPSG code of layer CRS.
        name (:obj:`str`, optional): Layer name. If None, then the `layer_type`
            is assigned as the name. Default: None.
    '''
    config = dict(CONFIG[layer_type.name])
    if name is None:
        name = layer_type.name.lower()
    vl = QgsVectorLayer(
        f"{config['geometry']}?crs=epsg:{crs}&index=yes", name, 'memory')
    vl.dataProvider().addAttributes(create_fields(config))
    vl.updateFields()
    return vl


@require_qgis
def create_fields(config):
    '''
    Return QgsFields container based on specified configuration.
    
    Parameters:
        config (Dict[str, str]): Configuration dictionary. Fields are specified
            by the keys ``field1``, ``field2``, etc. The value must contain a
            field name followed by a field type, separated by a comma, for
            instance, ``tag, QString``.
    
    Returns:
        qgis.core.QgsFields:
    '''
    fieldinfo = {k: v.replace(' ','').split(',')
                 for k, v in config.items() if k.startswith('field')}
    fields = QgsFields()
    for field_name, field_type in fieldinfo.values():
        fields.append(QgsField(field_name, QVariant.nameToType(field_type)))
    return fields


@require_qgis
def group_to_gpkg(group, directory=None, name=None, overwrite=False):
    '''
    Save the layers in a layer tree group as a GPKG.
    
    Parameters:
        group (:obj:`str` or :obj:`qgis.core.QgsLayerTreeGroup`): Layer tree
            group to export.
        directory (:obj:`str`, optional): Export directory. If None, then the
            project's home path is used. If the project does not have a home
            path, then ``NotADirectoryError`` is raised.
        name (:obj:`str`, optional): File name. If None, then the group's name
            is used.
        overwrite (:obj:`bool`, optional): If True and a GPKG already exists,
            then the existing file is overwritten. Default: False.
    
    Raises:
        NotADirectoryError: If a directory is not specified and the project has
            no home path.
        FileExistsError: If overwrite is False but a GPKG already exists.
    '''    
    if directory is None:
        directory = QgsProject.instance().homePath()
    if directory == '':
        raise NotADirectoryError(directory)
    
    if not os.path.isdir(directory):
        os.makedirs(directory)
    
    if name is None:
        name = group.name()
    path = os.path.join(directory, f'{name}.gpkg')
    if not overwrite and os.path.isfile(path):
        raise FileExistsError(path)
    
    layers = group.findLayers()
    context = QgsProject.instance().transformContext()
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'GPKG'
    
    for i, layer in enumerate(layers):
        layer = layer.layer()
        layer_name = layer.name()
        options.layerName = layer_name
        if i == 1:
            options.actionOnExistingFile = 1
        err_code, err_msg = QgsVectorFileWriter.writeAsVectorFormatV2(
            layer, path, context, options)
        if err_code != 0:
            print(err_msg)


@require_qgis
def point_feature_generator(vl, df, report):
    N = len(df)
    for i, row in df[['x', 'y']].iterrows():
        report(i/N*100)
        yield QgsVectorLayerUtils.createFeature(
            vl, QgsGeometry.fromPointXY(QgsPointXY(*row)))


def create_point_features(vl, df, report, cols=None):
    if cols is None:
        return list(point_feature_generator(vl, df, report))


@require_qgis
def generate_linestring_data(linestrings):
    pass


@require_qgis
def generate_polygon_data(polygons):
    pass

