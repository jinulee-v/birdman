# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import urllib3
import logging


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
        self.verbose = bool(obj['verbose'])


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

        string = 'Configuration for <%s>\n' % (self.name)
        for attr, value in sorted(vars(self.config).items()):
            string += "    {} = {}\n".format(attr, value)
        string += "\n"
        self.logger.info(string)
    
    def process_logger(self, stream=None, filename=None):
        # Formatter
        formatter = logging.Formatter('[%(levelname)s] ' + self.name 
+ ' %(asctime)s | %(message)s\n')
        
        # Handler
        handler = logging.StreamHandler(stream)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        if filename is not None:
            if isinstance(filename, str):
                filename = [filename]
            for file in filename:
                handler = logging.FileHandler(file, mode='a', encoding='UTF-8')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)

    async def stream(self):
        if self.config.verbose:
            self.show_config()

        try:
            async for result in self.job():
                yield result
        except urllib3.exceptions.ProtocolError:
            self.logger.warning("ProtocolError has raised but continue to stream.")
            self.stream()
        except RecursionError:
            return
        except KeyboardInterrupt:
            self.logger.error("User has interrupted.")
            return
