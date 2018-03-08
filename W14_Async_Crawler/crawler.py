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

from functools import partial
from datetime import datetime

from concurrent.futures import FIRST_EXCEPTION

import aiohttp
import async_timeout


LOGGER_FORMAT = '%(asctime)s %(message)s'
URL_TEMPLATE = "https://hacker-news.firebaseio.com/v0/item/{}.json"
TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
FETCH_TIMEOUT = 10
MAXIMUM_FETCHES = 1000
SITE_DIR = './sites'
LOG_WITH_DOWNLOADED_NEWS = 'downloaded.txt'

parser = argparse.ArgumentParser(
    description='Calculate the number of comments of the top stories in HN.')
parser.add_argument(
    '--period', type=int, default=15, help='Number of seconds between poll')
parser.add_argument(
    '--limit', type=int, default=2,
    help='Number of new stories to calculate comments for')
parser.add_argument('--verbose', action='store_true', help='Detailed output')


logging.basicConfig(format=LOGGER_FORMAT, datefmt='[%H:%M:%S]')
log = logging.getLogger()
log.setLevel(logging.INFO)


class BoomException(Exception):
    pass


class URLFetcher():
    """Provides counting of URL fetches for a particular task.
    """

    def __init__(self):
        self.fetch_counter = 0

    async def fetch(self, session, url):
        """Fetch a URL using aiohttp returning parsed JSON response.
        As suggested by the aiohttp docs we reuse the session.
        """
        with async_timeout.timeout(FETCH_TIMEOUT):
            self.fetch_counter += 1
            if self.fetch_counter > MAXIMUM_FETCHES:
                raise BoomException('BOOM!')

            async with session.get(url) as response:
                return await response.json()


def save_page(post_id, url, url_idx):
    curr_folder = os.path.abspath(os.path.join(SITE_DIR, str(post_id)))

    path = os.path.join(curr_folder, str(post_id) + '_' + str(url_idx) + '.html')

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    req = Request(url, headers=headers)

    gcontext = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    response = urlopen(req, context=gcontext)
    webContent = response.read()

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(webContent.decode('utf-8'))
    except BoomException as e:
        return print("Error loading content of website: {}".format(e))


def find_urls(result_page):
    res = None
    text = result_page.get('text', None)
    if text:
        html = Soup(text, 'html.parser')
        res = [a['href'] for a in html.find_all('a')]

        # exclude images
        list_of_extensions = ('png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp', 'svg', 'js')
        res = [s for s in res if not s.endswith(list_of_extensions)]

    return res

def calculate_nb_of_files(curr_folder):
    f_mask = '.html'
    counter = 0
    for f in os.listdir(curr_folder):
        if f.endswith(f_mask):
            counter +=1
    return counter


async def save_sites(loop, session, fetcher, post_id, parent_id):
    """Retrieve data for current post and recursively for all comments.
    """
    url = URL_TEMPLATE.format(post_id)
    try:
        response = await fetcher.fetch(session, url)
    except BoomException as e:
        log.debug("Error retrieving post {}: {}".format(post_id, e))
        raise e

    # base case, there are no response
    if response is None:
        return 0

    curr_folder = os.path.abspath(os.path.join(SITE_DIR, str(parent_id)))

    # create directory if is not exist
    if not os.path.exists(curr_folder):
        try:
            os.makedirs(curr_folder)
            curr_idx = 1
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    if os.path.exists(curr_folder):
        curr_idx = calculate_nb_of_files(curr_folder)+1

    with open(os.path.join(os.path.abspath(SITE_DIR), LOG_WITH_DOWNLOADED_NEWS), 'r', encoding='utf-8') as dl:
        content = dl.read()
        sites = content.split()

    if str(post_id) not in sites:

        # collect all arrays in new or comment
        url_array = []

        # collect url of parent site
        if response.get('url', None):
            url_array.append(response['url'])
        else:
            sites_from_comments = find_urls(response)
            if sites_from_comments is not None:
                # looking for urls in comments
                url_array += find_urls(response)

        if len(url_array):
            for url in list(set(url_array)):
                save_page(parent_id, url, curr_idx)
                curr_idx += 1

        sites.append(str(post_id))

        with open(os.path.join(os.path.abspath(SITE_DIR), LOG_WITH_DOWNLOADED_NEWS), 'w', encoding='utf-8') as dl:
            [dl.write("%s " % x) for x in sites]

    if 'kids' not in response:
        return curr_idx

    try:
        # create recursive tasks for all comments
        tasks = [asyncio.ensure_future(save_sites(
            loop, session, fetcher, kid_id, parent_id=parent_id)) for kid_id in response['kids']]

        # schedule the tasks and retrieve results
        try:
            await asyncio.gather(*tasks)
        except BoomException as e:
            log.debug("Error retrieving comments for top stories: {}".format(e))
            raise

        log.debug('{:^6} > saved {} sites'.format(post_id, curr_idx))

        return curr_idx

    except asyncio.CancelledError:
        if tasks:
            log.info("Comments for post {} cancelled, cancelling {} child tasks".format(
                post_id, len(tasks)))
            for task in tasks:
                task.cancel()
        else:
            log.info("Comments for post {} cancelled".format(post_id))
        raise


async def get_top_stories(loop, session, limit, iteration):
    """Retrieve top stories in HN.
    """
    fetcher = URLFetcher()  # create a new fetcher for this task
    try:
        response = await fetcher.fetch(session, TOP_STORIES_URL)
    except BoomException as e:
        log.error("Error retrieving top stories: {}".format(e))
        # return instead of re-raising as it will go unnoticed
        return
    except Exception as e:  # catch generic exceptions
        log.error("Unexpected exception: {}".format(e))
        return

    tasks = {
        asyncio.ensure_future(
            save_sites(loop, session, fetcher, post_id, parent_id=post_id)
        ): post_id for post_id in response[:limit]}

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
                tasks[done_task], done_task.result(), iteration))
        except BoomException as e:
            print("Error retrieving top stories: {}".format(e))

    return fetcher.fetch_counter


async def poll_top_stories(loop, session, period, limit):
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
            get_top_stories(loop, session, limit, iteration))

        now = datetime.now()

        def callback(fut, errors):
            try:
                fetch_count = fut.result()
            except BoomException as e:
                log.debug('Adding {} to errors'.format(e))
                errors.append(e)
            except Exception as e:
                log.exception('Unexpected error')
                errors.append(e)
            else:
                log.info(
                    '> Calculating comments took {:.2f} seconds and {} fetches'.format(
                        (datetime.now() - now).total_seconds(), fetch_count))

        future.add_done_callback(partial(callback, errors=errors))

        log.info("Waiting for {} seconds...".format(period))
        iteration += 1
        await asyncio.sleep(period)


async def main(args, lp):
    async with aiohttp.ClientSession(loop=lp) as session:
        await poll_top_stories(lp, session, args.period, args.limit)

if __name__ == '__main__':
    args = parser.parse_args()
    if args.verbose:
        log.setLevel(logging.DEBUG)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(args, loop))