"""
An example of periodically scheduling coroutines using an infinite loop of
scheduling a task using ensure_future and sleeping.
Artificially produce an error and use try..except clauses to catch them.
Use `wait` to cancel pending coroutines in case if an exception.
"""

import asyncio
import argparse
import logging
import os, errno
import ssl

from bs4 import BeautifulSoup as Soup
from urllib.request import urlopen, Request

from datetime import datetime

from concurrent.futures import FIRST_EXCEPTION

import aiohttp
import async_timeout
from concurrent.futures import ThreadPoolExecutor


LOGGER_FORMAT = '%(asctime)s %(message)s'
URL_TEMPLATE = "https://news.ycombinator.com/item?id={}"
TOP_STORIES_URL = "https://news.ycombinator.com"
FETCH_TIMEOUT = 10
MAXIMUM_FETCHES = 1000
SITE_DIR = './sites'
LOG_WITH_DOWNLOADED_NEWS = 'downloaded.txt'
EXTENSION_NOT_SAVE = ('png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp', 'svg', 'js')
NB_WORKERS_FOR_SITE_SAVING = 30
THREAD_POOL = ThreadPoolExecutor(int(NB_WORKERS_FOR_SITE_SAVING))


def calculate_nb_of_files(curr_folder):
    f_mask = '.html'
    counter = 0
    for f in os.listdir(curr_folder):
        if f.endswith(f_mask):
            counter += 1
    return counter


def parse_page(page, top=False):
    soup = Soup(page, 'html.parser')
    if top:
        top_news_list = []
        news_rows = soup.find_all('tr', class_='athing')
        for news_row in news_rows:
            top_news_list.append([news_row['id'], news_row.find('a', class_='storylink')['href']])
        return top_news_list
    else:
        comment_rows = soup.find_all('div', class_='comment')
        all_links_from_comment = []
        for comment in comment_rows:
            comment_text = comment.find('span', class_="c00")
            if comment_text:
                links_from_comment = [a.get('href', None) for a in comment_text.find_all('a')]
                if len(links_from_comment):
                    all_links_from_comment += links_from_comment
        # exclude images and refs for reply
        res = [s for s in all_links_from_comment if
               not s.endswith(EXTENSION_NOT_SAVE) and not s.startswith('reply')]
        return res


class URLFetcher():
    """Provides counting of URL fetches for a particular task.
    """

    def __init__(self):
        self.fetch_counter = 0

    async def fetch(self, session, url, top=False):
        """Fetch a URL using aiohttp returning parsed JSON response.
        As suggested by the aiohttp docs we reuse the session.
        """
        with async_timeout.timeout(FETCH_TIMEOUT):
            self.fetch_counter += 1
            if self.fetch_counter > MAXIMUM_FETCHES:
                raise Exception('Maximum number of fetches exceeded')

            async with session.get(url) as response:
                page = await response.read()
                return parse_page(page, top)


async def save_page(post_id, url, url_idx):
    curr_folder = os.path.abspath(os.path.join(SITE_DIR, str(post_id)))

    path = os.path.join(curr_folder, str(post_id) + '_' + str(url_idx) + '.html')

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    req = Request(url, headers=headers)

    gcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    response = urlopen(req, context=gcontext)
    webContent = response.read()

    try:
        with open(path, 'wb') as f:
            f.write(webContent)
    except Exception as e:
        return print("Error loading content of website: {}".format(e))


async def save_sites(session, fetcher, top_news_list):
    """Retrieve data for current post and recursively for all comments.
    """
    post_id = top_news_list[0]
    top_site_url = top_news_list[1]
    comments_url = URL_TEMPLATE.format(post_id)

    curr_folder = os.path.abspath(os.path.join(SITE_DIR, str(post_id)))
    url_array = []

    # create directory if is not exist
    if not os.path.exists(curr_folder):
        try:
            os.makedirs(curr_folder)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    curr_files_in_folder = calculate_nb_of_files(curr_folder)

    if not curr_files_in_folder:
        # get urls from comments
        try:
            sites_from_comments = await fetcher.fetch(session, comments_url)
        except Exception as e:
            log.debug("Error retrieving post {}: {}".format(post_id, e))
            raise e

        # add main site to url_list
        url_array.append(top_site_url)

        if len(sites_from_comments):
            url_array += sites_from_comments

        tasks = [asyncio.ensure_future(save_page(post_id, url, curr_idx))
                 for curr_idx, url in enumerate(url_array, start=1)]


        # schedule the tasks and retrieve results
        try:
            # await asyncio.gather(*tasks)
            await loop.run_in_executor(THREAD_POOL, *tasks)
        except Exception as e:
            log.debug("Error retrieving saving new sites: {}".format(e))
            raise
        return len(url_array)
    return curr_files_in_folder


async def get_top_stories(session, limit, iteration):
    """Retrieve top stories in HN.
    """
    fetcher = URLFetcher()  # create a new fetcher for this task
    try:
        response = await fetcher.fetch(session, TOP_STORIES_URL, top=True)
    except Exception as e:
        log.error("Error retrieving top stories: {}".format(e))
        # return instead of re-raising as it will go unnoticed
        return

    tasks = {
        asyncio.ensure_future(
            save_sites(session, fetcher, top_news_list)
        ): top_news_list for top_news_list in response[:limit]}

    # return on first exception to cancel any pending tasks
    done, pending = await asyncio.shield(asyncio.wait(
        tasks.keys(), return_when=FIRST_EXCEPTION))

    # if there are pending tasks is because there was an exception
    # cancel any pending tasks
    for pending_task in pending:
        pending_task.cancel()

    # process the done tasks
    for done_task in done:
        # if an exception is raised one of the Tasks will raise
        try:
            print("Post {} has {} saved sites ({})".format(
                tasks[done_task][0], done_task.result(), iteration))
        except Exception as e:
            print("Error retrieving top stories: {}".format(e))

    return fetcher.fetch_counter


async def poll_top_stories(session, period, limit):
    """Periodically poll for new stories and retrieve sites
    """
    iteration = 1
    errors = []
    while True:
        if errors:
            log.info('Error detected, quitting')
            return

        log.info("Searching sites top {} stories. ({})".format(
            limit, iteration))

        future = asyncio.ensure_future(
            get_top_stories(session, limit, iteration))

        now = datetime.now()

        def callback(fut):
            try:
                fetch_count = fut.result()
            except Exception as e:
                log.debug('Adding {} to errors'.format(e))

            else:
                log.info(
                    '> Process to save news took {:.2f} seconds and {} fetches'.format(
                        (datetime.now() - now).total_seconds(), fetch_count))

        future.add_done_callback(callback)

        log.info("Waiting for {} seconds...".format(period))
        iteration += 1
        await asyncio.sleep(period)


async def main(args, lp):
    async with aiohttp.ClientSession(loop=lp) as session:
        await poll_top_stories(session, args.period, args.limit)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download top stories in HN.')
    parser.add_argument(
        '--period', type=int, default=10, help='Number of seconds between poll')
    parser.add_argument(
        '--limit', type=int, default=30,
        help='Number of new stories to download')
    parser.add_argument('--verbose', action='store_true', help='Detailed output')

    args = parser.parse_args()

    logging.basicConfig(format=LOGGER_FORMAT, datefmt='[%H:%M:%S]')
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    if args.verbose:
        log.setLevel(logging.DEBUG)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(args, loop))
