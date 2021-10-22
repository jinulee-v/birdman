# AsyncIO
import asyncio
import aiostream

import yaml

from birdman.stream.base import BaseStreamer
from birdman.listen.base import BaseListener

from birdman.listen import get_listener
from birdman.stream import get_streamer


def init_birdman_from_yaml(file, encoding='UTF-8'):
    listeners = []
    listener_global = None
    streamers = []
    streamer_global = None

    with open(file, 'r', encoding=encoding) as file:
        obj = yaml.safe_load(file)
        for streamer in obj['streamer']:
            if streamer['class'] == 'global':
                if streamer_global is None:
                    streamer_global = {**streamer}
                    streamer_global.pop('class')
                else:
                    raise ValueError("Only a single `global` can be defined in streamers")
            else:
                if streamer_global is not None:
                    streamer = {**streamer, **streamer_global}
                streamers.append(get_streamer(streamer['class'])(streamer))
        for listener in obj['listener']:
            if listener['class'] == 'global':
                if listener_global is None:
                    listener_global = {**listener}
                    listener_global.pop('class')
                else:
                    raise ValueError("Only a single `global` can be defined in listeners")
            else:
                if listener_global is not None:
                    listener = {**listener, **listener_global}
                listeners.append(get_listener(listener['class'])(listener))

    return Birdman(streamers, listeners)


class Birdman(object):
    """Wrapper class that encapsulates the whole asynchronous routine.
    Provides interface that can modify streamers and listeners in the middle of a run.
    """

    def __init__(self, streamers, listeners):
        self._streamers = streamers
        self._listeners = listeners

        for streamer in streamers:
            if not isinstance(streamer, BaseStreamer):
                raise ValueError("`streamers` argument must be an iterable of BaseStreamer instances")
        for listener in listeners:
            if not isinstance(listener, BaseListener):
                raise ValueError("`listeners` argument must be an iterable of BaseListener instances")

    async def _stream_routine(self):
        """Asynchronous streaming & listening starts here.
        """
        self._stream = aiostream.stream.merge(*[
            streamer.stream() for streamer in self._streamers
        ])
        async with self._stream.stream() as streamer:
            async for name, item in streamer:
                for listener in self._listeners:
                    if listener.listen_to is None or name in listener.listen_to:
                        listener.listen(item)

    def start(self):
        """Main entry point of the Birdman object.
        """
        self.loop = asyncio.get_event_loop()

        try:
            self.loop.run_until_complete(self._stream_routine())
        finally:
            self.loop.close()

    def add_streamer(self, streamer):
        if not isinstance(streamer, BaseStreamer):
            raise ValueError("`streamer` argument must be a BaseStreamer instance")

        self.loop.stop()
        self._streamers.append(streamer)
        self.start()

    def add_listener(self, listener):
        if not isinstance(listener, BaseListener):
            raise ValueError("`listener` argument must be a BaseListener instance")

        self.loop.stop()
        self._listeners.append(listener)
        self.start()
