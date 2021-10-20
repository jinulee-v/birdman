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

class BaseStreamer(object):
    """BaseStreamer class contains:

    Methods:
        get_parser: returns initial argument parser
        show_options: show options that can be used or parsed
        stream: try asynchronous streaming using job method
    """

    def __init__(self, config_obj):
        self.config = BaseStreamerConfig(config_obj)

    def show_config(self):
        """Print out config available and predefined values."""

        for attr, value in sorted(vars(self.config).items()):
            print("{} = {}".format(attr, value))
        print()

    async def stream(self):
        if self.config.verbose:
            self.show_config()

        try:
            async for result in self.job():
                yield result
        except urllib3.exceptions.ProtocolError:
            print("ProtocolError has raised but continue to stream.")
            self.stream()
        except RecursionError:
            return
        except KeyboardInterrupt:
            print("User has interrupted.")
            return
