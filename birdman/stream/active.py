# -*- coding: utf-8 -*-
import asyncio
import aiohttp

from birdman.stream.base import BaseStreamer, BaseStreamerConfig

from abc import ABCMeta, abstractmethod

class ActiveStreamerConfig(BaseStreamerConfig):
    """Config object for Active Streamer.
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

class ActiveStreamer(BaseStreamer):
    """ActiveStreamer 
    ActiveStreamer routinely requests data within given interval.

    Methods:
        job: template for active parsing.
        - REQUIRES:
            get_post: crawl the post and generates result object(usually a dict).
            summary: generates and logs summary text for each result generated
        close:
            closes the streamer's aiohttp session.
    
    - inherited from BaseStreamer
        get_parser: returns initial argument parser
        show_options: show options that can be used or parsed
        set_logger: set logger configurations
        stream: try asynchronous streaming using job method
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        self._session = aiohttp.ClientSession()

    async def job(self):
        self.logger.info("Start of crawling epoch")

        new_post_id, new_datetime = self.config.current_post_id, self.config.current_datetime
        initial_result = True
        async for result in self.get_post():
            if initial_result:
                new_post_id, new_datetime = result['post_no'], result['written_at']
                initial_result = False
            if result is not None:
                self.summary(result)
            yield result

        if self.config.verbose:
            self.logger.info("End of crawling epoch(reached config.current_*)")
        self.config.set_current(new_post_id, new_datetime)
        await asyncio.sleep(self.config.recrawl_interval)
        self.job()

    async def close(self):
        await self._session.close()

    @abstractmethod
    async def get_post(self):
        '''Must override as a generator(i.e. yield not return).
        Generate one result at a time(usually a single post).
        
        Use `aiohttp` instead of `requests` to make asynchronous requests.
        Use self.config.page_interval to delay crawling.
        '''
        pass

    @abstractmethod
    async def summary(self, result):
        '''Override as a void function(i.e. no return value).
        
        Use self.logger to generate logs with the result(what get_post() yields).
        '''
        pass
