import difflib
import re
import io
import gzip
from urllib import request

import bs4

_NETWORK_ENABLED = True

MAIN_URL = 'https://www.tusubtitulo.com/'
SERIES_INDEX_URL = MAIN_URL + 'series.php'
SERIES_PAGE_PATTERN = MAIN_URL + 'show/{show}'
SEASON_PAGE_PATTERN = (MAIN_URL +
                       'ajax_loadShow.php?show={show}&season={season}')


class API:
    def __init__(self, fetch_func=None):
        if fetch_func is None:
            fetch_func = fetch_url
        self._fetch_func = fetch_func

    def fetch(self, url):
        return self._fetch_func(url)

    def get_show(self, show):
        def _get_id_from_url(url):
            m = re.match(
                MAIN_URL + 'show/(\d+)',
                url,
                flags=re.IGNORECASE)

            if not m:
                raise ValueError(url)

            return m.group(1)

        # Search exact match
        table = parse_index_page(
            self.fetch(SERIES_INDEX_URL),
            asdict=True)
        rev = {v: k for (k, v) in table.items()}

        if show in table:
            return ShowInfo(
                title=show,
                id=_get_id_from_url(table[show]),
                url=table[show])

        # Search by lowercase
        lc_table = {show.lower(): link for (show, link) in table.items()}
        lc_show = show.lower()
        if lc_show in lc_table:
            url = lc_table[lc_show]
            return ShowInfo(
                title=rev[url],
                id=_get_id_from_url(url),
                url=url)

        # Aproximate search
        ratios = [
            (key, difflib.SequenceMatcher(None, lc_show, key).ratio())
            for key in lc_table
        ]

        ratios = reversed(sorted(ratios, key=lambda x: x[1]))
        first = next(ratios)
        if first[1] >= 0.75:
            url = lc_table[first[0]]
            return ShowInfo(
                title=rev[url],
                id=_get_id_from_url(url),
                url=url)

        raise ShowNotFoundError(show)

    def get_subtitles(self, show, season, episode=None):
        language_table = {
            'english': 'en-US',
            'español (españa)': 'es-ES',
            'español (latinoamérica)': 'es-LAT'
        }

        showinfo = self.get_show(show)

        season_data = parse_season_page(self.fetch(
            SEASON_PAGE_PATTERN.format(show=showinfo.id, season=season)))

        ret = []
        for (ep, title, version, language, url) in season_data:
            if ep is not None and ep != episode:
                continue

            try:
                language = language_table[language.lower()]
            except KeyError:
                continue

            ret.append(SubtitleInfo(
                show=showinfo,
                season=season,
                ep=ep,
                version=version,
                language=language,
                url=url,
                title=title))

        return ret


class ShowInfo:
    def __init__(self, title, id, url):
        self.title = title
        self.id = id

        assert self.url == url

    @property
    def url(self):
        return SERIES_PAGE_PATTERN.format(show=self.id)


class SubtitleInfo:
    def __init__(self, show, season, ep, version, language, url, title=None):
        self.show = show
        self.season = season
        self.episode = ep
        self.title = title
        self.version = version
        self.language = language
        self.url = url

    def __repr__(self):
        fmt = (
            "<"
            "{mod}.{cls} "
            "{show} s:{season} e:{episode} ({language}/{version}) "
            "{url}>")

        return fmt.format(
            mod=__name__,
            cls=self.__class__.__name__,
            show=self.show.title,
            language=self.language,
            season=self.season,
            episode=self.episode,
            version=self.version,
            url=self.url)

#         if fetch is None:
#             fetch = fetch_url
#         self._fetch = fetch

#         if self.show is None and self.id is None:
#             raise ValueError('show or id is needed')

#         if not self.id:
#             self._get_show_info()

    # def _get_show_info(self):
    #     url = get_show_url(
    #         self.show,
    #         buff=self._fetch(self._SERIES_INDEX))

    #     m = re.match(
    #         'https://www.tusubtitulo.com/show/(\d+)',
    #         url,
    #         flags=re.IGNORECASE)
    #     if not m:
    #         raise ShowNotFoundError(self.show)

    #     self.id = m.group(1)

    # def get_episode_subtitles(self, season, episode):
    #     if season not in self._subtitle_info:
    #         self.fetch_season_info(season)

    #     return self._subtitle_info[season][episode]

    # def fetch_season_info(self, season):
    #     season_url = ('https://www.tusubtitulo.com/ajax_loadShow.php?'
    #                   'show={show_id}&season={season}')
    #     season_url = season_url.format(show_id=self.id, season=season)

    #     return season_url


    # def get_season_subtitles(self, season):
    #     season_url = self.get_season_url(season)
    #     subtitles = parse_season_page(self._fetch(season_url))



class ShowNotFoundError(Exception):
    def __init__(self, series, *args, **kwargs):
        self.show = series
        super().__init__(self, *args, **kwargs)



#
# Parsers
#

def _soupify(buff, encoding='utf-8', parser="html.parser"):
    return bs4.BeautifulSoup(buff.decode(encoding), parser)


def parse_index_page(buff, asdict=False):
    soup = _soupify(buff)
    
    ret = [
        (x.text, 'https://www.tusubtitulo.com' + x.attrs['href'])
        for x in soup.select('a')
        if x.attrs.get('href', '').startswith('/show/')
    ]

    if asdict:
        ret = {show: url for (show, url) in ret}

    return ret

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

            # print("Got episode {} header: {}".format(ep, title))

        # Version header
        elif td.attrs.get('colspan', '') == '3':
            curr_version = td.text.strip()
            curr_version = curr_version.split(' ', maxsplit=1)[1]
            # print("  Version:", curr_version)

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

    return ret

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
