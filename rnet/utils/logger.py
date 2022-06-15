import logging
import os
from pathlib import Path


def setup():
    logging.basicConfig(
        filename=os.path.join(Path(__file__).parents[2], 'LOG.log'),
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
