# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from koshort.threading import PropagatingThread
import urllib3


class KoshortStreamerError(Exception):
    def __init__(self, message, streamer):
        self.message = message
        self.streamer = streamer

    def __str__(self):
        return "%s has crashed. \n%s" % (self.streamer, self.message)


class BaseStreamerConfig(object):
    """Config object for BaseStreamer.
    """
    
    def __init__(self, obj):
        """
        Args:
            obj (dict): result of YAML parsing.
        """
        self.verbose = False
        self.is_async = True

class BaseStreamer(object):
    """BaseStreamer class contains:

    Methods:
        get_parser: returns initial argument parser
        show_options: show options that can be used or parsed
        stream: try asynchronous streaming using job method
    """

    def __init__(self, config_obj):
        self.config = BaseStreamerConfig(config_obj)

    def show_options(self):
        """Print out options available and predefined values."""

        for attr, value in sorted(vars(self.options).items()):
            print("{} = {}".format(attr, value))

    def stream(self):
        try:
            if self.config.is_async:
                self._thread = PropagatingThread(target=self.job)
                self._thread.start()
                self._thread.join()
            else:
                self.job()
        except urllib3.exceptions.ProtocolError:
            print("ProtocolError has raised but continue to stream.")
            self.stream()
        except RecursionError:
            return False
        except KeyboardInterrupt:
            print("User has interrupted.")
            return False
