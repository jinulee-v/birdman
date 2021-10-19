# -*- coding: utf-8 -*-
from koshort.stream.base import BaseStreamerConfig


class ActiveStreamerConfig(BaseStreamerConfig):
    """Config object for Active Streamer.
    Active Streamer routinely requests data within given interval.
    """

    def __init__(self, obj):
        """
        Args:
            obj (dict): result of YAML parsing.
        """
        super(ActiveStreamerConfig, self).__init__(obj)
        
        self.markup = 'html.parser'

        self.recrawl_interval = obj.get('recrawl_interval', 1800)

        self.timeout = obj.get('timeout', 5)
        self.page_interval = obj.get('page_interval', 0.5)

        # Custom header is required in order to request.
        self.header = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                       'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0'}
