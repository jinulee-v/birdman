# AsyncIO
import asyncio
from aiostream import stream
import aiohttp

# Parsing
from bs4 import BeautifulSoup

# Formatting
import re
from datetime import datetime
import colorama
from colorama import Style, Fore

from koshort.stream.base import BaseStreamer
from koshort.stream.active import ActiveStreamerConfig


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
        self.gallery_id = obj.get('gallery_id', 'cat')
        self.name = 'dcinside.' + self.gallery_id

        # Should we include comments? (str)
        self.include_comments = bool(obj.get('include_comments', 0))
        self.comments_per_page = obj.get('comments_per_page', 40)

        # When do we stop
        init_post_id = obj.get('current_post_id', 0)
        init_datetime = obj.get('current_datetime', "0000-00-00T00:00:00")
        self.set_current(init_post_id, init_datetime)

    def set_current(self, new_post_id, new_datetime):
        """Update current_post_id after finish crawling
        """
        self.current_post_id = new_post_id
        self.current_datetime = new_datetime


class DCInsideStreamer(BaseStreamer):
    """DCInside is a biggest community website in Korea.
    DCInsideStreamer helps to stream specific gallery from future to past.
    """

    def __init__(self, config_obj):

        self.config = DCInsideStreamerConfig(config_obj)

        self._session = aiohttp.ClientSession()

        self.set_logger()

        self._lists_url = 'http://gall.dcinside.com/board/lists'
        self._view_url = 'http://gall.dcinside.com'
        self._comment_view_url = 'http://gall.dcinside.com/board/view'

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
            except aiohttp.ServerTimeoutError:
                # if timeout occurs, retry
                continue

    async def get_post(self, gallery_id):
        """DCinside Post generator

        Args:
            gallery_id (str): Gallery ID

        Yields:
            post (dict): Dict object containing relevant information about the post
        """

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
                    except aiohttp.ServerTimeoutError:
                        # if timeout occurs, retry
                        continue
                    except AttributeError:
                        return

                if not isinstance(post, dict):
                    return

                post['url'] = url
                post['gallery_id'] = gallery_id
                post_no = int(re.search('no=([0-9]*)', url).group(1))
                post['post_no'] = post_no
                post['crawled_at'] = datetime.now().isoformat()

                if self.config.include_comments and 'comment_cnt' in post:
                    if post['comment_cnt'] > 0:
                        post['comments'] = self.get_all_comments(gallery_id, post_no, post['comment_cnt'])
                    else:
                        post['comments'] = []

                # Check if we have saw this post before
                if post_no <= self.config.current_post_id or post['written_at'] <= self.config.current_datetime:
                    # FIXME: Directly comparing datetime ISO-formatted string
                    return

                yield post
        except NoSuchGalleryError:
            return
        except AttributeError:
            return

    def get_all_comments(self, gallery_id, post_no, comment_cnt):
        """
        FIXME: get_all_comments() currently not available
        """
        return []
        # comment_page_cnt = (comment_cnt - 1) // self.config.comments_per_page + 1
        # comments = []
        # headers = {**self.config.header, **{'X-Requested-With': 'XMLHttpRequest'}}
        # data = {'ci_t': self._session.cookies['ci_c'], 'id': gallery_id, 'no': post_no}

        # for i in range(comment_page_cnt):
        #     data['comment_page'] = i + 1
        #     response = self._session.post(self._comment_view_url, headers=headers, data=data)

        #     batch = self.parse_comments(response.text)

        #     if not batch:
        #         break

        #     comments = batch + comments

        # return comments

    async def job(self):
        colorama.init()

        def summary(result):
            self.logger.debug(
                result['url'] + '\n' + # URL
                Fore.CYAN + result['title'] + Fore.RESET + '\n' + # Title
                Fore.CYAN + result['written_at'] + Fore.RESET + '\n' + # Written at
                Fore.RED + Style.DIM + result['nickname'] + Fore.RESET + '\n' + # Written by
                Fore.MAGENTA + '조회 %d / 추천 %d / 비추천 %d / 댓글 %d' % (result['view_cnt'], result['view_up'], result['view_dn'], result['comment_cnt']) + Fore.RESET + '\n\n' + # Statistics
                result['body'] # Body
            )

        self.logger.info("Start of crawling epoch")

        new_post_id, new_datetime = self.config.current_post_id, self.config.current_datetime
        initial_result = True
        async for result in self.get_post(self.config.gallery_id):
            if initial_result:
                new_post_id, new_datetime = result['post_no'], result['written_at']
                initial_result = False
            if result is not None:
                summary(result)
            yield result

        if self.config.verbose:
            self.logger.info("End of crawling epoch(reached config.current_post_id)")
        self.config.set_current(new_post_id, new_datetime)
        await asyncio.sleep(self.config.recrawl_interval)
        self.job()

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
            soup = BeautifulSoup(markup, parser).find('div', attrs={'class': 'gall_listwrap'})
            if '해당 갤러리는 존재하지 않습니다' in str(soup):
                raise NoSuchGalleryError
        except:
            return None

        raw_post_list = soup.find_all('tr', attrs={'class': 'us-post'})

        # remove NOTICE posts(fixed at the top of the list)
        post_list = [
            tr.find('a')['href'] for tr in raw_post_list
            if tr['data-type'] == "icon_txt"
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
            soup = BeautifulSoup(markup, parser).find('div', attrs={'class': 'view_content_wrap'})
            if '해당 갤러리는 존재하지 않습니다' in str(soup):
                raise NoSuchGalleryError
        except:
            return None

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

        body = soup.find('div', attrs={'class': 'write_div'}).getText().strip()

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

    @staticmethod
    def parse_comments(text):
        """
        FIXME: parse_comments() currently not available
        """
        return []
        # comments = []
        # soup = BeautifulSoup(text, 'html5lib')
        # comment_elements = soup.find_all('tr', class_='reply_line')

        # for element in comment_elements:
        #     user_layer = element.find('td', class_='user_layer')
        #     nickname = user_layer['user_name']
        #     user_id = user_layer['user_id']
        #     body = element.find('td', class_='reply')
        #     user_ip = '' if user_id else body.find('span').extract().text
        #     timestamp = element.find('td', class_='retime').text

        #     comment = {
        #         'user_id': user_id,
        #         'user_ip': user_ip,
        #         'nickname': nickname,
        #         'written_at': timestamp,
        #         'body': body.text.strip()
        #     }

        #     comments.append(comment)

        # return comments


class NoSuchGalleryError(Exception):
    pass


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