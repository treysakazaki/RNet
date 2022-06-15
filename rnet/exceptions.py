from functools import wraps

try:
    import qgis.core
except:
    QGIS_AVAILABLE = False
else:
    QGIS_AVAILABLE = True


class Error(Exception):
    pass


class ConfigError(Error):
    '''
    Raised if layer utilities could not load configuration file.
    '''
    def __init__(self):
        super().__init__("'config.ini' could not be loaded")


class DuplicateSourceError(Error):
    '''
    Raised if a source that already exists is added to a DataContainer.
    '''
    def __init__(self, source_name):
        super().__init__(f'{source_name!r} has already been added')


class NotAvailableError(Error):
    '''
    Raised if a function depends on an unavailable package.
    '''
    def __init__(self, func_name, pkg_name):
        super().__init__(f'{func_name!r} requires {pkg_name}')


def require_qgis(func):
    '''
    Wrapper for functions that require ``qgis.core``.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        if QGIS_AVAILABLE:
            result = func(*args, **kwargs)
        else:
            raise NotAvailableError(func.__name__, 'QGIS')
        return result
    return wrapper
