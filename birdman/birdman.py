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

    async def _stream_routine(self):
        """Asynchronous streaming & listening starts here.
        """
        self._stream = aiostream.stream.merge([
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
            self.loop.run_forever(self._stream_routine())
        finally:
            self.loop.close()

    def add_streamer(self, streamer):
        if not isinstance(streamer, BaseStreamer):
            raise ValueError("Streamer object must inherit from BaseStreamer")

        self.loop.stop()
        self._streamers.append(streamer)
        self.start()

    def add_listener(self, listener):
        if not isinstance(listener, BaseListener):
            raise ValueError("Listener object must inherit from BaseListener")

        self.loop.stop()
        self._listeners.append(listener)
        self.start()
