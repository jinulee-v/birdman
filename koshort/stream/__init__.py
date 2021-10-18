"""High-level streaming interfaces for various websites and services"""

from __future__ import absolute_import

from koshort.stream.base import BaseStreamer, KoshortStreamerError

from koshort.stream.twitter import TwitterStreamer
from koshort.stream.dcinside import DCInsideStreamer
