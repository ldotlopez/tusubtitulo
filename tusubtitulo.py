import difflib
import re
from urllib import request

import bs4

_NETWORK_ENABLED = True


class ShowInfo:
    def __init__(self, show=None, id=None, fetch=None):
        self.show = show
        self.id = id

        if fetch is None:
            fetch = fetch_url
        self._fetch = fetch

        if self.show is None and self.id is None:
            raise ValueError('show or id is needed')

        if not self.id:
            self._get_show_info()

    def _get_show_info(self):
        url = get_show_url(
            self.show,
            buff=self._fetch('https://www.tusubtitulo.com/series.php'))

        m = re.match(
            'https://www.tusubtitulo.com/show/(\d+)',
            url,
            flags=re.IGNORECASE)
        if not m:
            raise SeriesNotFoundError(self.show)

        self.id = m.group(1)

    def get_episode_subtitles(self, season, episode):
        if season not in self._subtitle_info:
            self.fetch_season_info(season)

        return self._subtitle_info[season][episode]

    def fetch_season_info(self, season):
        season_url = ('https://www.tusubtitulo.com/ajax_loadShow.php?'
                      'show={show_id}&season={season}')
        season_url = season_url.format(show_id=self.id, season=season)

        return season_url


    def get_season_subtitles(self, season):
        season_url = self.get_season_url(season)
        subtitles = parse_season_page(self._fetch(season_url))



class SeriesNotFoundError(Exception):
    def __init__(self, series, *args, **kwargs):
        self.show = series
        super().__init__(self, *args, **kwargs)

#
# High level functions
#


def get_show_url(series, buff):
    if buff is None:
        buff = fetch_url('https://www.tusubtitulo.com/series.php')

    table = {series: link for (series, link) in parse_index_page(buff)}
    if series in table:
        return table[series]

    lc_table = {series.lower(): link for (series, link) in table.items()}
    lc_series = series.lower()
    if lc_series in lc_table:
        return lc_table[lc_series]

    ratios = [
        (key, difflib.SequenceMatcher(None, lc_series, key).ratio())
        for key in lc_table
    ]

    ratios = reversed(sorted(ratios, key=lambda x: x[1]))
    first = next(ratios)
    if first[1] >= 0.75:
        return lc_table[first[0]]

    raise SeriesNotFoundError(series)


#
# Parsers
#

def _soupify(buff, encoding='utf-8', parser="html.parser"):
    return bs4.BeautifulSoup(buff.decode(encoding), parser)


def parse_index_page(buff):
    soup = _soupify(buff)
    series_links = [
        (x.text, 'https://www.tusubtitulo.com' + x.attrs['href'])
        for x in soup.select('a')
        if x.attrs.get('href', '').startswith('/show/')
    ]

    return series_links


def parse_season_page(buff):
    ret = []

    curr_title = None
    curr_ep = None
    curr_version = None

    soup = _soupify(buff)
    for td in soup.select('td'):

        # Episode title header
        if td.attrs.get('colspan', '') == '5':

            # Get title
            title = td.text.strip()
            if ' - ' in title:
                title = title.split(' - ', maxsplit=1)[1]

            # Get episode number
            m = re.search(
                r'/\d+/(\d+)/\d+/',  # season/episode/show_id
                td.select_one('a').attrs['href'])
            ep = m.group(1)

            curr_ep = ep
            curr_title = title

            print("Got episode {} header: {}".format(ep, title))

        # Version header
        elif td.attrs.get('colspan', '') == '3':
            curr_version = td.text.strip()
            curr_version = curr_version.split(' ', maxsplit=1)[1]
            print("  Version:", curr_version)

        elif 'language' in td.attrs.get('class', []):
            language = td.text.strip()

            completed_node = td.findNextSibling('td')
            completed = completed_node.text.strip().lower() == 'completado'
            if completed is False:
                continue

            link_node = completed_node.findNextSibling('td').select_one('a')
            if link_node is None:
                continue

            try:
                href = 'https:' + link_node.attrs['href']
            except KeyError:
                continue

            ret.append((
                curr_ep,
                curr_title,
                curr_version,
                language,
                href
            ))


#
# Network
#
def fetch_url(url, headers=None):
    if not _NETWORK_ENABLED:
        raise RuntimeError('Network not enabled')

    default_headers = {
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86) Home software '
                       '(KHTML, like Gecko)'),
        'Accept-Language': 'en, en-gb;q=0.9, en-us;q=0.9'
    }

    if headers is None:
        headers = {}

    for (k, v) in default_headers.items():
        if k not in headers:
            headers[k] = v

    req = request.Request(url, headers=headers)
    resp = request.urlopen(req)
    if resp.getheader('Content-Encoding') == 'gzip':
        bi = io.BytesIO(resp.read())
        gf = gzip.GzipFile(fileobj=bi, mode="rb")
        buff = gf.read()
    else:
        buff = resp.read()

    return buff
