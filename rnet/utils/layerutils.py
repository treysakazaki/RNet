from configparser import ConfigParser
from enum import Enum, auto
import os

try:
    from qgis.core import QgsProject, QgsVectorFileWriter
except:
    pass

from rnet.exceptions import require_qgis


class LayerType(Enum):
    '''
    Enumeration of layer types.
    '''
    VERTICES = auto()
    LINKS = auto()
    NODES = auto()
    EDGES = auto()


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

