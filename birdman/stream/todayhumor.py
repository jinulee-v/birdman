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
from colorama import Style, Fore

from birdman.stream import register_streamer
from birdman.stream.active import ActiveStreamer, ActiveStreamerConfig


class TodayHumorStreamerConfig(ActiveStreamerConfig):
    """Config object for TodayHumorStreamer.
    """

    def __init__(self, obj):
        """
        Args:
            obj (dict): result of YAML parsing.
        """
        super(TodayHumorStreamerConfig, self).__init__(obj)

        # Markup parser: override ActiveStreamerConfig
        # self.markup = 'html5lib'

        # TodayHumor Board ID (str)
        self.board_id = obj.get('board_id', 'animal')
        self.name = 'todayhumor.' + self.board_id

        # Should we include comments? (str)
        self.include_comments = bool(obj.get('include_comments', 0))

        # When do we stop
        init_post_id = obj.get('current_post_id', 0)
        init_datetime = obj.get('current_datetime', "0000-00-00T00:00:00")
        self.set_current(init_post_id, init_datetime)

    def set_current(self, new_post_id, new_datetime):
        """Update current_post_id after finish crawling
        """
        self.current_post_id = new_post_id
        self.current_datetime = new_datetime


@register_streamer("todayhumor")
class TodayHumorStreamer(ActiveStreamer):
    """TodayHumor is a liberal-side community about various subjects.
    TodayHumorStreamer helps to stream specific board from future to past.
    """

    def __init__(self, config_obj):

        self.config = TodayHumorStreamerConfig(config_obj)

        self._session = aiohttp.ClientSession()

        self.set_logger()
        # Use colorama
        colorama.init()

        # FIXME someday we should all turn over from raw HTML parsing to API
        self._lists_url = 'http://www.todayhumor.co.kr/board/list.php'
        self._view_url = 'http://www.todayhumor.co.kr'
        # self._comment_api_url = 'http://app.TodayHumor.com/api/comment_new.php'

    def summary(self, result):
        """summary function for TodayHumor.
        """
        text = ''
        text += result['url'] + '\n' # URL
        text += Fore.CYAN + result['title'] + Fore.RESET + '\n' # Title
        text += Fore.CYAN + result['written_at'] + Fore.RESET + '\n' # Written at
        text += Fore.RED + result['nickname'] + Fore.RESET + '\n' # Written by
        text += Fore.MAGENTA + '조회 %d / 추천 %d / 댓글 %d' % (result['view_cnt'], result['view_updn'], result['comment_cnt']) + Fore.RESET + '\n\n' # Statistics
        text += result['body'] + '\n\n' # Body
        if self.config.include_comments:
            for comment in result['comments']:
                text += Fore.RED + comment['nickname'] + Fore.RESET + ' (' + comment['written_at'] + ') | ' + comment['body'] + '\n'
                for subcomment in comment['subcomments']:
                    text += '└ ' + Fore.RED + subcomment['nickname'] + Fore.RESET + ' (' + subcomment['written_at'] + ') | ' + subcomment['body'] + '\n'

        self.logger.debug(text)

    async def get_post(self):
        """Post generator for TodayHumor.
        get_post is ALWAYS the main custom entry point of the ActiveCrawler.

        Args:
            board_id (str): Board ID

        Yields:
            post (dict): Dict object containing relevant information about the post
        """

        board_id = self.config.board_id
        try:
            async for url in self.get_post_list(board_id):
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
                    except aiohttp.ServerTimeoutError:
                        # if timeout occurs, retry
                        continue
                    except AttributeError:
                        return

                if not isinstance(post, dict):
                    return

                post['url'] = url
                post['board_id'] = board_id
                post_no = int(re.search('no=([0-9]*)', url).group(1))
                post['post_no'] = post_no
                post['crawled_at'] = datetime.now().isoformat()

                if self.config.include_comments and 'comment_cnt' in post:
                    # if post['comment_cnt'] > 0:
                    #     post['comments'] = await self.get_all_comments(board_id, post_no)
                    # else:
                        post['comments'] = []

                # Check if we have saw this post before
                if post_no <= self.config.current_post_id or post['written_at'] <= self.config.current_datetime:
                    # FIXME: Directly comparing datetime ISO-formatted string
                    return

                yield post
        except NoSuchBoardError:
            return
        except AttributeError:
            return

    async def get_post_list(self, board_id):
        """TodayHumor Post generator

        Args:
            board_id (str): Board ID

        Yields:
            url (str): URL for the next post found
        """
        page = 1
        while True:
            try:
                url = '%s?table=%s&page=%d' % (self._lists_url, board_id, page)
                await asyncio.sleep(self.config.page_interval)
                async with self._session.get(
                    url,
                    headers=self.config.header,
                    timeout=self.config.timeout
                ) as response:
                    post_list = self.parse_post_list(await response.text(), self.config.markup)
                    for url in post_list:
                        yield self._view_url + re.sub('&s_no=[0-9]+&page=[0-9]*', '', url)
                page += 1
            except aiohttp.ServerTimeoutError:
                # if timeout occurs, retry
                continue
        
    async def get_all_comments(self, board_id, post_no):
        """Get all comments by TodayHumor mobile app API.
        """
        comments = []
        async with self._session.get(
                            '%s?id=%s&no=%s' % (self._comment_api_url, board_id, post_no),
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

    @staticmethod
    def parse_post_list(markup, parser):
        """BeatifulSoup based post list parser

        Args:
            markup (str): response.text
            parser (str): parser option for bs4.

        Returns:
            post_list (list): List object containing URL(after domain only) of posts within the page 
        """

        try:
            soup = BeautifulSoup(markup, parser).find('table', attrs={'class': 'table_list'})
            if '해당 갤러리는 존재하지 않습니다' in str(soup):
                raise NoSuchBoardError
        except NoSuchBoardError:
            return None

        raw_post_list = soup.find_all('td', attrs={'class': 'subject'})

        # remove NOTICE posts(fixed at the top of the list)
        post_list = [
            tr.find('a')['href'] for tr in raw_post_list
        ]
        return post_list

    @staticmethod
    def parse_post(markup, parser):
        """BeatifulSoup based post parser

        Args:
            markup (str): response.text
            parser (str): parser option for bs4.

        Returns:
            post (dict): Dict object containing relevant information about the post
        """
        try:
            soup = BeautifulSoup(markup, parser).find('div', attrs={'class': 'containerInner'})
            # FIXME: if wrong ID,
            # if '해당 갤러리는 존재하지 않습니다' in str(soup):
            #     raise NoSuchBoardError
        except NoSuchBoardError:
            # FIXME categorize exceptions
            return None

        post_info = soup.find('div', attrs={'class': 'writerInfoContents'})

        user_id = post_info.find('span', attrs={'id': 'viewPageWriterNameSpan'})['mn']
        nickname = post_info.find('span', attrs={'id': 'viewPageWriterNameSpan'})['name']

        view_updn = int(post_info.find('span', attrs={'class', 'view_ok_nok'}).getText())
        
        for div in post_info.find_all('div'):
            if u'등록시간' in div.get_text():
                timestamp = div.getText().strip().replace(u'등록시간 : ', '')
                timestamp = datetime.strptime(timestamp, "%Y/%m/%d %H:%M:%S").isoformat()
            elif u'조회수' in div.get_text():
                view_cnt = int(div.getText().replace(u'조회수 : ', ''))
            elif u'댓글' in div.get_text():
                comment_cnt = int(div.getText().replace(u'댓글 : ', '').replace(u'개', ''))
            elif 'IP' in div.get_text():
                user_ip = div.getText().replace('IP : ', '')

        title = soup.find('div', attrs={'class': 'viewSubjectDiv'}).getText().strip()

        body = soup.find('div', attrs={'class': 'viewContent'}).get_text('\n', strip=True)

        post = {
            'user_id': user_id,
            'user_ip': user_ip,
            'nickname': nickname,

            'title': title,
            'written_at': timestamp,

            'view_updn': view_updn,
            'view_cnt': view_cnt,
            'comment_cnt': comment_cnt,
            'body': body,
        }

        return post


class NoSuchBoardError(Exception):
    pass


async def main():
    app1 = TodayHumorStreamer({
        'verbose': 1,
        'board_id': 'animal',
        'current_datetime': "2021-01-20",
        'page_interval': 5,
        'recrawl_interval': 60,
        'include_comments': 0
    })
    app = stream.merge(app1.stream())
    async with app.stream() as streamer:
        async for item in streamer:
            pass


if __name__ == "__main__":
    asyncio.run(main())