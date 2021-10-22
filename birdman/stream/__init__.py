"""High-level streaming interfaces for various websites and services"""

from __future__ import absolute_import

from birdman.stream.base import BirdmanStreamerError, BaseStreamer
import os

# registration decorator for streamers (accessed by config['class'])
_streamers = {}
def register_streamer(name):
    def decorator(cls):
        if not issubclass(cls, BaseStreamer):
            raise ValueError("decorator `register_streamer` must be used for BaseStreamer subclass")
        _streamers[name] = cls
        return cls
    return decorator


# Import all subpackages
for module in os.listdir(os.path.dirname(__file__)):
    if module == '__init__.py' or module[-3:] != '.py':
        continue
    __import__('birdman.stream.'+module[:-3], locals(), globals())
del module


# getter for streamer class
def get_streamer(name):
    """Return streamer class by its name.
    """
    return _streamers[name]