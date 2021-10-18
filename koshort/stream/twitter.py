# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import time
import tweepy
import tweepy.asynchronous
import colorama  # Colorama streaming verbosity.

from koshort.constants import DATA_DIR, ALPHABET
from koshort.stream import BaseStreamer
from koshort.utils import delete_links, delete_mentions


class KoshortTwitterStream(tweepy.Stream):
    def __init__(self, options, dirname, word_list):
        """KoshortTwitterStream is a tweepy listener to listen on filtered list of words.

        Args:
            options (object): argparser argument namespace
            dirname (str): string of directory
            word_list (list): list of words
        """

        # WARNING: This underlining keys and tokens
        # should not be shared or uploaded on any public code repository!
        self.consumer_key = options.consumer_key
        self.consumer_secret = options.consumer_secret
        self.access_token = options.access_token
        self.access_token_secret = options.access_token_secret
        
        super(KoshortTwitterStream, self).__init__(
            self.consumer_key, self.consumer_secret,
            self.access_token, self.access_token_secret
        )

        self.dirname = dirname
        self.words = word_list
        self.options = options

        self.limit = 0
        self.init_time = time.time()

        colorama.init()

    def on_status(self, status):
        tweet = status.text

        # Except potentially repetitive retweets
        def write_tweets_to_files(tweet):
            if self.options.remove_links:
                tweet = delete_links(tweet)
            if self.options.remove_mentions:
                tweet = delete_mentions(tweet)

            word_count = 0

            if not self.options.output_as_onefile:
                # counts how many targeting words included in one tweet.
                for word in self.words:
                    word_count += tweet.count(word)

            filename = "{}{}{}.{}".format(
                self.dirname,
                self.options.output_prefix,
                word_count,
                self.options.output_extension
            )

            n_word_file = open(filename, 'a', encoding='utf-8')
            n_word_file.write(tweet)
            n_word_file.write("\n")

            if self.options.verbose:
                for word in self.words:
                    tweet = (colorama.Fore.CYAN + word).join(tweet.split(word))
                    tweet = (word + colorama.Fore.RESET).join(tweet.split(word))
                print(word_count, tweet)

        if self.options.filter_retweets:
            if not "RT @" in tweet:
                write_tweets_to_files(tweet)
                self.limit += 1
                if (self.limit == self.options.tweet_limits) | (
                        (time.time() - self.init_time) >= self.options.time_limits):
                    return False

        else:
            write_tweets_to_files(tweet)
            self.limit += 1
            if self.limit == self.options.tweet_limits:
                return False

    def on_error(self, status_code):
        if status_code == 420:  # if connection failed
            return False

        
class KoshortTwitterAsyncStream(tweepy.asynchronous.AsyncStream):
    def __init__(self, options, dirname, word_list):
        """KoshortTwitterStream is a tweepy listener to listen on filtered list of words.
        Async version of KoshortTwitterStream.

        Args:
            options (object): argparser argument namespace
            dirname (str): string of directory
            word_list (list): list of words
        """

        # WARNING: This underlining keys and tokens
        # should not be shared or uploaded on any public code repository!
        self.consumer_key = options.consumer_key
        self.consumer_secret = options.consumer_secret
        self.access_token = options.access_token
        self.access_token_secret = options.access_token_secret
        
        super(KoshortTwitterAsyncStream, self).__init__(
            self.consumer_key, self.consumer_secret,
            self.access_token, self.access_token_secret
        )

        self.dirname = dirname
        self.words = word_list
        self.options = options

        self.limit = 0
        self.init_time = time.time()

        colorama.init()

    def on_status(self, status):
        tweet = status.text

        # Except potentially repetitive retweets
        def write_tweets_to_files(tweet):
            if self.options.remove_links:
                tweet = delete_links(tweet)
            if self.options.remove_mentions:
                tweet = delete_mentions(tweet)

            word_count = 0

            if not self.options.output_as_onefile:
                # counts how many targeting words included in one tweet.
                for word in self.words:
                    word_count += tweet.count(word)

            filename = "{}{}{}.{}".format(
                self.dirname,
                self.options.output_prefix,
                word_count,
                self.options.output_extension
            )

            n_word_file = open(filename, 'a', encoding='utf-8')
            n_word_file.write(tweet)
            n_word_file.write("\n")

            if self.options.verbose:
                for word in self.words:
                    tweet = (colorama.Fore.CYAN + word).join(tweet.split(word))
                    tweet = (word + colorama.Fore.RESET).join(tweet.split(word))
                print(word_count, tweet)

        if self.options.filter_retweets:
            if not "RT @" in tweet:
                write_tweets_to_files(tweet)
                self.limit += 1
                if (self.limit == self.options.tweet_limits) | (
                        (time.time() - self.init_time) >= self.options.time_limits):
                    return False

        else:
            write_tweets_to_files(tweet)
            self.limit += 1
            if self.limit == self.options.tweet_limits:
                return False

    def on_error(self, status_code):
        if status_code == 420:  # if connection failed
            return False

class TwitterStreamer(BaseStreamer):
    """Start streaming on Twitter with your api keys and tokens.

    Args:
        dirname (str): directory to save output files.
        word_list (list): list of words to be streamed.
        async (bool): if true, apply threading in tweepy layer.
    """

    def __init__(self, dirname=DATA_DIR, word_list=ALPHABET, is_async=True):
        self.is_async = is_async

        parser = self.get_parser()
        parser.add_argument(
            '--consumer_key',
            help='consumer key',
        )
        parser.add_argument(
            '--consumer_secret',
            help='consumer secret',
        )
        parser.add_argument(
            '--access_token',
            help='access token',
        )
        parser.add_argument(
            '--access_token_secret',
            help='access token secret',
        )
        parser.add_argument(
            '--filter_retweets',
            help='do not save potentially repetitive retweets',
            action="store_true",
        )
        parser.add_argument(
            '--remove_links',
            help='remove links included into each tweet',
            action="store_true",
        )
        parser.add_argument(
            '--remove_mentions',
            help='remove mentions included into each tweet',
            action="store_true",
        )
        parser.add_argument(
            '--output_prefix',
            help='prefix of the output file',
            default='tweet',
            type=str
        )
        parser.add_argument(
            '--output_as_onefile',
            help='save output as onefile',
            action="store_true",
        )
        parser.add_argument(
            '--output_extension',
            help='extension of the output file',
            default='txt',
            type=str
        )
        parser.add_argument(
            '--tweet_limits',
            help='stop when this amount of tweets are collected',
            default=1000000,
            type=int
        )
        parser.add_argument(
            '--time_limits',
            help='stop when n secs elapsed',
            default=1000000,
            type=int
        )
        parser.add_argument(
            '--keyword_file',
            help='file that defines a keywords line by line',
            type=str
        )

        self.options, _ = parser.parse_known_args()

        # lazy requirement checking since argparse's required option blocks initialization.
        requirements = [self.options.consumer_key, self.options.consumer_secret,
                        self.options.access_token, self.options.access_token_secret]

        requirements_check = False
        for requirement in requirements:
            if not requirement:
                requirements_check = True

        if not requirements_check:
            print("You have to provide valid consumer key, consumer_secret, access_token, access_token_secret.")

        # Parse wordlist from custom argument
        self.dirname = dirname
        if self.options.keyword_file is not None:
            try:
                reader = open(self.options.keyword_file, mode='r+', encoding='utf-8')
            except UnicodeDecodeError:
                reader = open(self.options.keyword_file, mode='r+', encoding='cp949')
            self.word_list = reader.readlines()

        else:
            self.word_list = word_list

        self.is_async = is_async
        self.stream = None

    def create_listener(self):

        if self.is_async:
            self.stream = KoshortTwitterStream(
                self.options, self.dirname, self.word_list
            )
        else:
            self.stream = KoshortTwitterAsyncStream(
                self.options, self.dirname, self.word_list
            )

    def job(self):
        self.stream.filter(track=self.word_list, threaded=True)


def main():
    app = TwitterStreamer(is_async=False)
    app.options.verbose = True
    app.show_options()
    app.create_listener()
    app.stream()


if __name__ == '__main__':
    main()
