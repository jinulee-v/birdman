# AsyncIO
import asyncio
from aiostream import stream
import aiohttp

# Parsing
from bs4 import BeautifulSoup

# Formatting
import re
import json
from datetime import datetime
import colorama
from colorama import Fore

from birdman.stream import register_streamer
from birdman.stream.active import ActiveStreamer, ActiveStreamerConfig
from birdman.error import ParserUpdateRequiredError, UnknownError


class DCInsideStreamerConfig(ActiveStreamerConfig):
    """Config object for DCInsideStreamer.
    """

    def __init__(self, obj):
        """
        Args:
            obj (dict): result of YAML parsing.
        """
        super(DCInsideStreamerConfig, self).__init__(obj)

        # Markup parser: override ActiveStreamerConfig
        self.markup = 'html5lib'

        # DCInside Gallery ID (str)
        self.gallery_id = obj.get('gallery_id', 'animal')
        self.minor_gallery = obj.get('minor_gallery', 0)
        self.name = 'dcinside.' + ('minor.' if self.minor_gallery else '') + self.gallery_id

        # Should we include comments? (str)
        self.include_comments = bool(obj.get('include_comments', 1))

        # When do we stop
        init_post_id = obj.get('current_post_id', 0)
        init_datetime = obj.get('current_datetime', "0000-00-00T00:00:00")
        self.set_current(init_post_id, init_datetime)

    def set_current(self, new_post_id, new_datetime):
        """Update current_post_id after finish crawling
        """
        self.current_post_id = new_post_id
        self.current_datetime = new_datetime


@register_streamer("dcinside")
class DCInsideStreamer(ActiveStreamer):
    """DCInside is a biggest community website in Korea.
    DCInsideStreamer helps to stream specific gallery from future to past.

    Special credits to "KotlinInside" & JellyBrick@github for finding perfect API endpoints
    """

    def __init__(self, config_obj):
        super(DCInsideStreamer, self).__init__()

        self.config = DCInsideStreamerConfig(config_obj)

        self.set_logger()
        # Use colorama
        colorama.init()

        # FIXME someday we should all turn over from raw HTML parsing to API
        self._lists_url = 'http://gall.dcinside.com{}/board/lists'.format('/mgallery' if self.config.minor_gallery else '')
        self._view_url = 'http://gall.dcinside.com'
        self._comment_api_url = 'http://app.dcinside.com/api/comment_new.php'

    def summary(self, result):
        """summary function for DCInside.
        """
        text = ''
        text += result['url'] + '\n' # URL
        text += Fore.CYAN + result['title'] + Fore.RESET + '\n' # Title
        text += Fore.CYAN + result['written_at'] + Fore.RESET + '\n' # Written at
        text += Fore.RED + result['nickname'] + Fore.RESET + '\n' # Written by
        text += Fore.MAGENTA + '조회 %d / 추천 %d / 비추천 %d / 댓글 %d' % (result['view_cnt'], result['view_up'], result['view_dn'], result['comment_cnt']) + Fore.RESET + '\n\n' # Statistics
        text += result['body'] + '\n\n' # Body
        if self.config.include_comments:
            for comment in result['comments']:
                text += Fore.RED + comment['nickname'] + Fore.RESET + ' (' + comment['written_at'] + ') | ' + comment['body'] + '\n'
                for subcomment in comment['subcomments']:
                    text += '└ ' + Fore.RED + subcomment['nickname'] + Fore.RESET + ' (' + subcomment['written_at'] + ') | ' + subcomment['body'] + '\n'

        self.logger.debug(text)

    async def get_post(self):
        """Post generator for DCInside.
        get_post is ALWAYS the main custom entry point of the ActiveCrawler.

        Args:
            gallery_id (str): Gallery ID

        Yields:
            post (dict): Dict object containing relevant information about the post
        """

        gallery_id = self.config.gallery_id
        try:
            async for url in self.get_post_list(gallery_id):
                while True:
                    try:
                        # Site's anti-bot policy may block crawling & you can consider gentle crawling
                        await asyncio.sleep(self.config.page_interval)

                        async with self._session.get(
                            url,
                            headers=self.config.header,
                            timeout=self.config.timeout
                        ) as response:

                            post = self.parse_post(await response.text(), self.config.markup)
                            break
                    except (aiohttp.ServerTimeoutError, asyncio.TimeoutError):
                        # if timeout occurs, retry
                        continue
                    except aiohttp.InvalidURL:
                        raise ParserUpdateRequiredError(self.config.name, "Invalid URL. Website or API address may has changed.")

                if not isinstance(post, dict):
                    return

                post['url'] = url
                post['gallery_id'] = gallery_id
                post_no = int(re.search('no=([0-9]*)', url).group(1))
                post['post_no'] = post_no
                post['crawled_at'] = datetime.now().isoformat()

                if self.config.include_comments and 'comment_cnt' in post:
                    if post['comment_cnt'] > 0:
                        post['comments'] = await self.get_all_comments(gallery_id, post_no)
                    else:
                        post['comments'] = []

                # Check if we have saw this post before
                if post_no <= self.config.current_post_id or post['written_at'] <= self.config.current_datetime:
                    # FIXME: Directly comparing datetime ISO-formatted string
                    return

                yield post
        except GeneratorExit:
            raise GeneratorExit()
        except ParserUpdateRequiredError as e:
            raise e
        except:
            raise UnknownError(self.config.name)

    async def get_post_list(self, gallery_id):
        """DCinside Post generator

        Args:
            gallery_id (str): Gallery ID

        Yields:
            url (str): URL for the next post found
        """
        page = 1
        while True:
            try:
                url = '%s?id=%s&page=%d' % (self._lists_url, gallery_id, page)
                await asyncio.sleep(self.config.page_interval)
                async with self._session.get(
                    url,
                    headers=self.config.header,
                    timeout=self.config.timeout
                ) as response:
                    post_list = self.parse_post_list(await response.text(), self.config.markup)
                    for url in post_list:
                        yield self._view_url + re.sub('&page=[0-9]*', '', url)
                page += 1
            except (aiohttp.ServerTimeoutError, asyncio.TimeoutError):
                # if timeout occurs, retry
                continue
            except aiohttp.InvalidURL:
                raise ParserUpdateRequiredError(self.config.name, "Invalid URL. Website or API address may has changed.")
        
    async def get_all_comments(self, gallery_id, post_no):
        """Get all comments by DCInside mobile app API.
        """
        comments = []
        try:
            async with self._session.get(
                                '%s?id=%s&no=%s' % (self._comment_api_url, gallery_id, post_no),
                                headers=self.config.header,
                                timeout=self.config.timeout
                            ) as response:

                response = json.loads(await response.text())
                for comment in response[0]['comment_list']:
                    comment_data = {
                            'user_id': comment['user_id'],
                            'user_ip': comment['ipData'],
                            'nickname': comment['name'],

                            'written_at': datetime.strptime(comment['date_time'], "%Y.%m.%d %H:%M").isoformat(),

                            'body': re.sub('(<br>)+', '\n', comment['comment_memo']),

                            'subcomments': []
                    }
                    if 'under_step' not in comment:
                        comments.append(comment_data)
                    else:
                        comments[-1]['subcomments'].append(comment_data)
                return comments
        except aiohttp.InvalidURL:
            raise ParserUpdateRequiredError(self.config.name, "Invalid URL. Website or API address may has changed.")
        except (aiohttp.ServerTimeoutError, asyncio.TimeoutError):
            return await self.get_all_comments(gallery_id, post_no)
        except RecursionError:
            return []

    def parse_post_list(self, markup, parser):
        """BeatifulSoup based post list parser

        Args:
            markup (str): response.text
            parser (str): parser option for bs4.

        Returns:
            post_list (list): List object containing URL(after domain only) of posts within the page 
        """

        try:
            soup = BeautifulSoup(markup, parser).find('div', attrs={'class': 'gall_listwrap'})
            if '해당 갤러리는 존재하지 않습니다' in str(soup):
                raise ParserUpdateRequiredError(self.config.name, "Gallery `%s` does not exists in DCInside." % self.config.board_id)

            raw_post_list = soup.find_all('tr', attrs={'class': 'us-post'})
            # remove NOTICE posts(fixed at the top of the list)
            post_list = [
                tr.find('a')['href'] for tr in raw_post_list
            ]
            return post_list
        except (AttributeError, KeyError) as er:
            raise ParserUpdateRequiredError(self.config.name, "Post list webpage HTML structure may has been changed.")

        raise UnknownError(self.config.name)

    def parse_post(self, markup, parser):
        """BeatifulSoup based post parser

        Args:
            markup (str): response.text
            parser (str): parser option for bs4.

        Returns:
            post (dict): Dict object containing relevant information about the post
        """
        try:
            soup = BeautifulSoup(markup, parser).find('div', attrs={'class': 'view_content_wrap'})
            if '해당 갤러리는 존재하지 않습니다' in str(soup):
                raise ParserUpdateRequiredError(self.config.name, "Gallery `%s` does not exists in DCInside." % self.config.board_id)

            timestamp = soup.find('span', attrs={'class': 'gall_date'}).getText()
            timestamp = datetime.strptime(timestamp, "%Y.%m.%d %H:%M:%S").isoformat()

            user_info = soup.find('div', attrs={'class': 'gall_writer'})
            user_id = user_info['data-uid']
            user_ip = user_info['data-ip']
            nickname = user_info['data-nick']

            view_cnt = int(soup.find('span', attrs={'class': 'gall_count'}).getText().replace(u'조회 ', ''))
            view_up = int(soup.find('p', attrs={'class', 'up_num'}).getText())
            view_dn = int(soup.find('p', attrs={'class', 'down_num'}).getText())
            comment_cnt = int(soup.find('span', attrs={'class': 'gall_comment'}).getText().replace(u'댓글 ', ''))

            title = soup.find('span', attrs={'class': 'title_subject'}).getText()

            body = soup.find('div', attrs={'class': 'write_div'}).get_text('\n', strip=True)

            post = {
                'user_id': user_id,
                'user_ip': user_ip,
                'nickname': nickname,

                'title': title,
                'written_at': timestamp,

                'view_up': view_up,
                'view_dn': view_dn,
                'view_cnt': view_cnt,
                'comment_cnt': comment_cnt,
                'body': body,
            }

            return post
        except (AttributeError, KeyError) as er:
            raise ParserUpdateRequiredError(self.config.name, "Post webpage HTML structure may has been changed.")

        raise UnknownError(self.config.name)


async def main():
    app1 = DCInsideStreamer({
        'verbose': 1,
        'gallery_id': 'cat',
        'current_datetime': "2021-10-20",
        'page_interval': 5,
        'recrawl_interval': 60
    })
    app2 = DCInsideStreamer({
        'verbose': 1,
        'gallery_id': 'dog',
        'current_datetime': "2021-10-20",
        'page_interval': 10,
        'recrawl_interval': 60
    })
    app = stream.merge(app1.stream(), app2.stream())
    async with app.stream() as streamer:
        async for item in streamer:
            pass


if __name__ == "__main__":
    asyncio.run(main())