# AsyncIO
import asyncio
import aiostream

from birdman.stream.base import BaseStreamer
from birdman.listen.base import BaseListener


class Birdman(object):
    """Wrapper class that encapsulates the whole asynchronous routine.
    Provides interface that can modify streamers and listeners in the middle of a run.
    """

    def __init__(self, streamers, listeners):
        self._streamers = streamers
        self._listeners = listeners
        
        for streamer in streamers:
            if not isinstance(streamer, BaseStreamer):
                raise ValueError("`streamers` argument must be an iterable of BaseStreamer objects")
        for listener in listeners:
            if not isinstance(listener, BaseListener):
                raise ValueError("`listeners` argument must be an iterable of BaseListener objects")

    async def _stream_routine(self):
        """Asynchronous streaming & listening starts here.
        """
        self._stream = aiostream.stream.merge(*[
            streamer.stream() for streamer in self._streamers
        ])
        async with self._stream.stream() as streamer:
            async for item in streamer:
                for listener in self._listeners:
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
            raise ValueError("`streamer` argument must be a BaseStreamer object")

        self.loop.stop()
        self._streamers.append(streamer)
        self.start()

    def add_listener(self, listener):
        if not isinstance(listener, BaseListener):
            raise ValueError("`listener` argument must be a BaseListener object")

        self.loop.stop()
        self._listeners.append(listener)
        self.start()


def main():
    from birdman.stream.dcinside import DCInsideStreamer
    from birdman.stream.todayhumor import TodayHumorStreamer

    streamers = [
        DCInsideStreamer({'verbose': 1}),
        TodayHumorStreamer({'verbose': 1, 'include_comments': 0})
    ]
    birdman = Birdman(streamers, [])
    birdman.start()


if __name__ == '__main__':
    main()