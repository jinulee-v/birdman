"""High-level streaming interfaces for various websites and services"""

from __future__ import absolute_import

import os

from birdman.listen.base import BaseListener

# registration decorator for listeners (accessed by config['class'])
_listeners = {}
def register_listener(name):
    def decorator(cls):
        if not issubclass(cls, BaseListener):
            raise ValueError("decorator `register_listener` must be used for BaseListener subclass")
        _listeners[name] = cls
        return cls
    return decorator


# Import all subpackages
for module in os.listdir(os.path.dirname(__file__)):
    if module == '__init__.py' or module[-3:] != '.py':
        continue
    __import__('birdman.listen.'+module[:-3], locals(), globals())
del module


# getter for listener class
def get_listener(name):
    """Return streamer class by its name.
    """
    return _listeners[name]