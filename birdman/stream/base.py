# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import urllib3
import logging

from abc import ABCMeta, abstractmethod


class BirdmanStreamerError(Exception):
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
        self.verbose = bool(obj.get('verbose', 0))


class BaseStreamer(object):
    """BaseStreamer class contains:

    Methods:
        get_parser: returns initial argument parser
        show_options: show options that can be used or parsed
        set_logger: set logger configurations
        stream: try asynchronous streaming using job method
    """

    __metaclass__ = ABCMeta

    def __init__(self, config_obj):
        self.config = BaseStreamerConfig(config_obj)

    def show_config(self):
        """Print out config available and predefined values."""

        string = 'Configuration for <%s>\n' % (self.config.name)
        for attr, value in sorted(vars(self.config).items()):
            string += "    {} = {}\n".format(attr, value)
        self.logger.info(string)

    def set_logger(self, stream=None, filename=None):
        # logger
        self.logger = logging.getLogger('asyncio.koshort.stream.' + self.config.name)
        if self.config.verbose:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARNING)

        # Formatter
        formatter = logging.Formatter('[%(levelname)s] ' + self.config.name 
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
                yield self.config.name, result
        except urllib3.exceptions.ProtocolError:
            self.logger.warning("ProtocolError has raised but continue to stream.")
            self.stream()
        except RecursionError:
            self.logger.error("RecursionError; too much retries")
            return

    @abstractmethod
    async def job(self):
        '''Must override as a generator(i.e. yield not return).
        Generate one result at a time.
        '''
        pass

    @abstractmethod
    async def close(self):
        '''Must override.
        How to properly close this streamer?
        '''
        pass