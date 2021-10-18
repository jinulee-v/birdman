# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from koshort.stream import DCInsideStreamer
import glob


def test_dcinside_streamer(is_async):
    streamer = DCInsideStreamer(is_async=is_async)
    streamer.options.gallery_id = 'cat'
    streamer.options.verbose = True
    streamer.options.final_post_id = 5
    streamer.stream()

def main():
    test_dcinside_streamer(True)
    test_dcinside_streamer(False)
    
if __name__ == "__main__":
    main()