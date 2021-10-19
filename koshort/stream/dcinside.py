from datetime import datetime
import re
from bs4 import BeautifulSoup
from koshort.stream import BaseStreamer

import requests
import time
import colorama

from colorama import Style, Fore
from pprint import pprint


class DCInsideStreamer(BaseStreamer):
    """DCInside is a biggest community website in Korea.
    DCInsideStreamer helps to stream specific gallery from past to future.
    """

    def __init__(self, markup='html5lib', is_async=True):
        self.is_async = is_async

        parser = self.get_parser()
        parser.add_argument(
            '--include_comments',
            help='include comments',
            action='store_true'
        )
        parser.add_argument(
            '--comments_per_page',
            help='comments per page to be crawled',
            default=40,
            type=int
        )
        parser.add_argument(
            '--gallery_id',
            help='specify gallery id such as: cat, dog',
            default='cat',
            type=str
        )
        parser.add_argument(
            '--init_post_id',
            help='initial post_id to start crawling',
            default=0,
            type=int
        )
        parser.add_argument(
            '--timeout',
            help='crawling timeout per request',
            default=5,
            type=float
        )
        parser.add_argument(
            '--interval',
            help='crawling interval per request to prevent blocking',
            default=0.5,
            type=float
        )
        parser.add_argument(
            '--metadata_to_dict',
            help='return metadata into dictionary type',
            action='store_true',
        )
        parser.add_argument(
            '--filename',
            help="filename to be saved.",
            default="gallery.txt"
        )

        self.options, _ = parser.parse_known_args()
        self._session = requests.Session()
        self._markup = markup
        self._lists_url = 'http://gall.dcinside.com/board/lists' 
        self._view_url = 'http://gall.dcinside.com'
        self._comment_view_url = 'http://gall.dcinside.com/board/view'
        self._current_post_id = self.options.init_post_id

        # Custom header is required in order to request.
        self.header = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                       'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0'}

    def get_post_list(self, gallery_id):
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
                response = self._session.get(
                    url,
                    headers=self.header,
                    timeout=self.options.timeout
                )
                post_list = self.parse_post_list(response.text, 'html5lib')
                for url in post_list:
                    yield self._view_url + re.sub('&page=[0-9]*', '', url)
                page += 1
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout):
                # if timeout occurs, retry
                continue

    def get_post(self, gallery_id):
        """DCinside Post generator

        Args:
            gallery_id (str): Gallery ID

        Yields:
            post (dict): Dict object containing relevant information about the post
        """

        try:
            for url in self.get_post_list(gallery_id):
                # Check if we have saw this post before
                post_no = int(re.search('no=([0-9]*)', url).group(1))
                if post_no <= self._current_post_id:
                    return

                while True:
                    try:
                        # Site's anti-bot policy may block crawling & you can consider gentle crawling
                        time.sleep(self.options.interval)

                        response = self._session.get(
                            url,
                            headers=self.header,
                            timeout=self.options.timeout
                        )

                        post = self.parse_post(response.text, 'html5lib')
                        break
                    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout):
                        # if timeout occurs, retry
                        continue
                    except AttributeError:
                        return None

                if not isinstance(post, dict):
                    return None

                post['url'] = url
                post['gallery_id'] = gallery_id
                post['post_no'] = post_no
                post['crawled_at'] = datetime.now().isoformat()

                if self.options.include_comments and 'comment_cnt' in post:
                    if post['comment_cnt'] > 0:
                        post['comments'] = self.get_all_comments(gallery_id, post_no, post['comment_cnt'])
                    else:
                        post['comments'] = []
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
        # comment_page_cnt = (comment_cnt - 1) // self.options.comments_per_page + 1
        # comments = []
        # headers = {**self.header, **{'X-Requested-With': 'XMLHttpRequest'}}
        # data = {'ci_t': self._session.cookies['ci_c'], 'id': gallery_id, 'no': post_no}

        # for i in range(comment_page_cnt):
        #     data['comment_page'] = i + 1
        #     response = self._session.post(self._comment_view_url, headers=headers, data=data)
            
        #     batch = self.parse_comments(response.text)

        #     if not batch:
        #         break

        #     comments = batch + comments

        # return comments

    def job(self):
        colorama.init()

        def summary(result):
            if not self.options.metadata_to_dict:
                if self.options.verbose:
                    print(Fore.CYAN + result['title'] + Fore.RESET)
                    print(Fore.CYAN + Style.DIM + result['written_at'] + Style.RESET_ALL + Fore.RESET)
                    print(Fore.RED + Style.DIM + result['nickname'] + Style.RESET_ALL + Fore.RESET)
                    print(Fore.MAGENTA + Style.DIM + '조회 %d / 추천 %d / 비추천 %d / 댓글 %d' % (result['view_cnt'], result['view_up'], result['view_dn'], result['comment_cnt']) + Style.RESET_ALL + Fore.RESET)
                    print(result['body'])
                    print()
                # TODO
                # Database update code
            else:
                if self.options.verbose:
                    pprint(result)


        for result in self.get_post(self.options.gallery_id):
            if result is not None:
                summary(result)

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


def main():
    app = DCInsideStreamer(is_async=False)
    app.options.verbose = True
    app.stream()


if __name__ == "__main__":
    main()
