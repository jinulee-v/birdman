# AsyncIO
import asyncio
from aiostream import stream
import aiohttp

# Tweepy interface
import tweepy
import tweepy.asynchronous
from oauthlib.oauth1 import Client as OAuthClient
from yarl import URL

import tweepy
from tweepy.errors import TweepyException
from tweepy.models import Status

# Formatting
import re
import json
from datetime import datetime
import colorama
from colorama import Style, Fore

from birdman.stream import register_streamer
from birdman.stream.base import BaseStreamer, BaseStreamerConfig
from birdman.error import ParserUpdateRequiredError, UnknownError
from birdman.utils import delete_links, delete_mentions


class TwitterStreamerConfig(BaseStreamerConfig):
    """Config object for all TwitterStreamer classes.
    """

    def __init__(self, obj):
        """
        Args:
            obj (dict): result of YAML parsing.
        """
        super(TwitterStreamerConfig, self).__init__(obj)

        # TodayHumor Board ID (str)
        assert 'auth' in obj
        assert 'twitter' in obj['auth']
        self.consumer_key = obj['auth']['twitter'].get('consumer_key')
        self.consumer_secret = obj['auth']['twitter'].get('consumer_secret')
        self.access_token = obj['auth']['twitter'].get('access_token')
        self.access_token_secret = obj['auth']['twitter'].get('access_token_secret')

        # filteration options
        self.remove_links = bool(obj.get('remove_links', True))
        self.remove_mentions = bool(obj.get('remove_mentions', False))
        # remove retweets?
        self.filter_retweets = bool(obj.get('filter_retweets', True))


class TwitterKeywordStreamerConfig(TwitterStreamerConfig):
    """Config object for all TwitterStreamer classes.
    """

    def __init__(self, obj):
        """
        Args:
            obj (dict): result of YAML parsing.
        """
        super(TwitterKeywordStreamerConfig, self).__init__(obj)

        # Keywords to filter
        self.word_list = obj.get('word_list')
        # if only single word is given,
        if not isinstance(self.word_list, list):
            # list-ify it
            self.word_list = [self.word_list]

        # streamer is named after its first keyword
        self.name = "twitterkeyword." + self.word_list[0]


class BirdmanTwitterAsyncStream(tweepy.asynchronous.AsyncStream):
    def __init__(self, config):
        """
        Args:
            config (object): argparser argument namespace
            dirname (str): string of directory
            word_list (list): list of words
        """
        self.config = config

        # WARNING: This underlining keys and tokens
        # should not be shared or uploaded on any public code repository!
        self.consumer_key = config.consumer_key
        self.consumer_secret = config.consumer_secret
        self.access_token = config.access_token
        self.access_token_secret = config.access_token_secret
        
        super(BirdmanTwitterAsyncStream, self).__init__(
            self.consumer_key, self.consumer_secret,
            self.access_token, self.access_token_secret
        )

        self.words = config.word_list

        colorama.init()

    async def on_status(self, status):
        tweet = status._json
        
        timestamp = tweet['created_at']
        # "Sun Nov 14 10:08:16 +0000 2021"
        timestamp = datetime.strptime(timestamp, "%a %b %d %H:%M:%S %z %Y").isoformat()
        
        tweet = {
            'url': "twitter.com/%s/status/%s" % (tweet['user']['screen_name'], tweet['id_str']),

            'user_id': tweet['user']['id_str'],
            'nickname': tweet['user']['screen_name'],

            'written_at': timestamp,

            "quote_cnt": tweet["quote_count"],
            "reply_cnt": tweet["reply_count"],
            "retweet_cnt": tweet["retweet_count"],
            "favorite_cnt": tweet["favorite_count"],

            'body': tweet['text'],
        }
        if 'retweeted_status' in tweet:
            retweet = status._json['retweeted_status']
            retweet = {
                'url': "twitter.com/%s/status/%s" % (retweet['user']['screen_name'], tweet['id_str']),

                'user_id': retweet['user']['id_str'],
                'nickname': retweet['user']['screen_name'],

                'written_at': retimestamp,

                "quote_cnt": retweet["quote_count"],
                "reply_cnt": retweet["reply_count"],
                "retweet_cnt": retweet["retweet_count"],
                "favorite_cnt": retweet["favorite_count"],

                'body': retweet['text'],
            }
            tweet['retweet'] = retweet

        # Except potentially repetitive retweets
        if self.config.remove_links:
            tweet['body'] = delete_links(tweet['body'])
        if self.config.remove_mentions:
            tweet['body'] = delete_mentions(tweet['body'])

        if self.config.filter_retweets:
            if not "RT @" in tweet:
                return tweet
        else:
            return tweet

    async def on_error(self, status_code):
        if status_code == 420:  # if connection failed
            return False

    async def _connect(self, method, endpoint, params={}, headers=None, body=None):
        """Override of original coroutine '_connect' to async_generator
        since tweepy does not support `yield`ing instead of on_status() handling.
        """
        error_count = 0
        # https://developer.twitter.com/en/docs/twitter-api/v1/tweets/filter-realtime/guides/connecting
        stall_timeout = 90
        network_error_wait = network_error_wait_step = 0.25
        network_error_wait_max = 16
        http_error_wait = http_error_wait_start = 5
        http_error_wait_max = 320
        http_420_error_wait_start = 60

        oauth_client = OAuthClient(self.consumer_key, self.consumer_secret,
                                   self.access_token, self.access_token_secret)

        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": self.user_agent},
                timeout=aiohttp.ClientTimeout(sock_read=stall_timeout)
            )

        url = f"https://stream.twitter.com/1.1/{endpoint}.json"
        url = str(URL(url).with_query(sorted(params.items())))

        try:
            while error_count <= self.max_retries:
                request_url, request_headers, request_body = oauth_client.sign(
                    url, method, body, headers
                )
                try:
                    async with self.session.request(
                        method, request_url, headers=request_headers,
                        data=request_body, proxy=self.proxy
                    ) as resp:
                        if resp.status == 200:
                            error_count = 0
                            http_error_wait = http_error_wait_start
                            network_error_wait = network_error_wait_step

                            await self.on_connect()

                            async for line in resp.content:
                                line = line.strip()
                                if line:
                                    # Only change is made here to yield the data.
                                    yield await self.on_data(line)
                                else:
                                    await self.on_keep_alive()

                            await self.on_closed(resp)
                        else:
                            await self.on_request_error(resp.status)

                            error_count += 1

                            if resp.status == 420:
                                if http_error_wait < http_420_error_wait_start:
                                    http_error_wait = http_420_error_wait_start

                            await asyncio.sleep(http_error_wait)

                            http_error_wait *= 2
                            if resp.status != 420:
                                if http_error_wait > http_error_wait_max:
                                    http_error_wait = http_error_wait_max
                except (aiohttp.ClientConnectionError,
                        aiohttp.ClientPayloadError) as e:
                    await self.on_connection_error()

                    await asyncio.sleep(network_error_wait)

                    network_error_wait += network_error_wait_step
                    if network_error_wait > network_error_wait_max:
                        network_error_wait = network_error_wait_max
        except asyncio.CancelledError:
            return
        except Exception as e:
            await self.on_exception(e)
        finally:
            await self.session.close()
            await self.on_disconnect()

            
    def filter(self, *, follow=None, track=None, locations=None, filter_level=None, languages=None, stall_warnings=False):
        """Filter realtime Tweets; overrided
        """
        if self.task is not None and not self.task.done():
            raise TweepyException("Stream is already connected")

        endpoint = "statuses/filter"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        body = {}
        if follow is not None:
            body["follow"] = ','.join(map(str, follow))
        if track is not None:
            body["track"] = ','.join(map(str, track))
        if locations is not None:
            if len(locations) % 4:
                raise TweepyException(
                    "Number of location coordinates should be a multiple of 4"
                )
            body["locations"] = ','.join(
                f"{location:.4f}" for location in locations
            )
        if filter_level is not None:
            body["filter_level"] = filter_level
        if languages is not None:
            body["language"] = ','.join(map(str, languages))
        if stall_warnings:
            body["stall_warnings"] = "true"

        # Override to handler _connect() as an async_generator
        return self._connect("POST", endpoint, headers=headers, body=body or None)

@register_streamer("twitterkeyword")
class TwitterKeywordStreamer(BaseStreamer):
    """Twitter is a global short-text SNS.
    TwitterKeywordStreamer filters tweets by keywords using tweepy asynchronous API.
    (Basically, this class is a birdman wrapper for tweepy.)
    """
    def __init__(self, config_obj):
        """
        """
        self.config = TwitterKeywordStreamerConfig(config_obj)
        self._stream = BirdmanTwitterAsyncStream(self.config)
        self._task = self._stream.filter(track=self.config.word_list, filter_level='None')

        self.set_logger()
    
    def summary(self, result):
        for word in self.config.word_list:
            body = result['body']
            body = (colorama.Fore.CYAN + word).join(body.split(word))
            body = (word + colorama.Fore.RESET).join(body.split(word))
        
        text = ''
        text += result['url'] + '\n' # URL
        text += Fore.CYAN + result['written_at'] + Fore.RESET + '\n' # Written at
        text += Fore.RED + result['nickname'] + Fore.RESET + '\n' # Written by
        text += Fore.MAGENTA +'Quote %d / Reply %d / Retweet %d / Favorite %d' % (result['quote_cnt'], result['reply_cnt'], result['retweet_cnt'], result['favorite_cnt']) + Fore.RESET + '\n\n' # Statistics
        text += result['body'] + '\n\n' # Body
        if 'retweet' in result:
            retweet = result['retweet']

            text += 'RT from:\n'
            text += '  ' + retweet['url'] + '\n' # URL
            text += '  ' + Fore.CYAN + retweet['written_at'] + Fore.RESET + '\n' # Written at
            text += '  ' + Fore.RED + retweet['nickname'] + Fore.RESET + '\n' # Written by
            text += '  ' + Fore.MAGENTA +'Quote %d / Reply %d / Retweet %d / Favorite %d' % (retweet['quote_cnt'], retweet['reply_cnt'], retweet['retweet_cnt'], retweet['favorite_cnt']) + Fore.RESET + '\n\n' # Statistics
            text += '  ' + retweet['body'] + '\n\n' # Body

        self.logger.debug(text)
    
    async def job(self):
        async for result in self._task:
            if self.config.verbose:
                self.summary(result)
            yield result

    async def close(self):
        self._stream.disconnect()


async def main():
    # create auth.yaml in main directory and add:
    """
    twiiter:
        consumer_key: YOUR_TOKEN
        consumer_secret: YOUR_TOKEN
        access_token: YOUR_TOKEN
        access_token_secret: YOUR_TOKEN
    """
    with open('auth.yaml', 'r') as file:
        auth = yaml.safe_load(file)
        # print(auth)
    app1 = TwitterKeywordStreamer({
        'verbose': 1,
        'word_list': ['bird', 'birdman'],
        'auth': auth
    })
    app = stream.merge(app1.stream())
    async with app.stream() as streamer:
        async for item in streamer:
            pass


if __name__ == "__main__":
    import yaml
    asyncio.run(main())