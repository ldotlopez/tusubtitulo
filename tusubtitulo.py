# -*- encoding: utf-8 -*-


# Compatibity stuff
from __future__ import unicode_literals, print_function


import difflib
import re
import sys
from os import path


import bs4
import guessit
import requests


_NETWORK_ENABLED = True

MAIN_URL = 'http://www.tusubtitulo.com/'
SERIES_INDEX_URL = MAIN_URL + 'series.php'
SERIES_PAGE_PATTERN = MAIN_URL + 'show/{show}'
SEASON_PAGE_PATTERN = (MAIN_URL +
                       'ajax_loadShow.php?show={show}&season={season}')


class API(object):
    def __init__(self, fetcher=None):
        if fetcher is None:
            fetcher = Fetcher()
        self._fetcher = fetcher

    def fetch(self, url, headers={}):
        # print("===> Fetch {}".format(url))
        return self._fetcher.fetch(url, headers)

    def get_show(self, show):
        def _get_id_from_url(url):
            m = re.match(
                MAIN_URL + 'show/(\d+)',
                url,
                flags=re.IGNORECASE)

            if not m:
                raise ValueError(url)

            return m.group(1)

        buff = self.fetch(
            SERIES_INDEX_URL,
            {'Referer': MAIN_URL}
        )

        # Search exact match
        table = parse_index_page(buff)
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
            'english': 'en-us',
            'español (españa)': 'es-es',
            'español (latinoamérica)': 'es-lat'
        }

        showinfo = self.get_show(show)
        buff = self.fetch(
            SEASON_PAGE_PATTERN.format(show=showinfo.id, season=season),
            {'Referer': showinfo.url}
        )
        season_data = parse_season_page(buff)

        state = self._fetcher.get_state()
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
                title=title,
                params=state))

        return ret

    def get_subtitles_from_filename(self, filename):
        info = guessit.guessit(filename)

        if info['type'] != 'episode':
            raise ValueError('Invalid episode filename:' + filename)

        for f in 'title season episode'.split(' '):
            if f not in info or info[f] in (None, ''):
                raise ValueError('Invalid episode filename:' + filename)

        return self.get_subtitles(
            info['title'], str(info['season']), str(info['episode']))

    def fetch_subtitle(self, subtitle_info):
        headers = {
            'Referer': SEASON_PAGE_PATTERN.format(
                show=subtitle_info.show.id,
                season=subtitle_info.season)
        }
        return self.fetch(subtitle_info.url, headers)


class ShowInfo(object):
    def __init__(self, title, id, url):
        self.title = title
        self.id = id

        assert self.url == url

    @property
    def url(self):
        return SERIES_PAGE_PATTERN.format(show=self.id)


class SubtitleInfo(object):
    def __init__(self, show, season, ep, version, language, url, params={},
                 title=None):
        self.show = show
        self.season = season
        self.episode = ep
        self._title = title
        self.version = version
        self.language = language
        self.url = url
        self.params = params

    @property
    def title(self):
        if self._title:
            return self._title

        else:
            return "{show} - s{season:02d}xe{episode:02d}".format(
                show=self.show.title,
                season=self.season,
                episode=self.episode)

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


class ShowNotFoundError(Exception):
    def __init__(self, series, *args, **kwargs):
        self.show = series
        super(ShowNotFoundError, self).__init__(*args, **kwargs)


#
# Parsers
#

def _soupify(buff, encoding='utf-8', parser="html.parser"):
    # return bs4.BeautifulSoup(buff.decode(encoding), parser)
    return bs4.BeautifulSoup(buff, parser)


def parse_index_page(buff):
    soup = _soupify(buff)

    return {
        x.text: 'http://www.tusubtitulo.com' + x.attrs['href']
        for x in soup.select('a')
        if x.attrs.get('href', '').startswith('/show/')
    }


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
            # if ' - ' in title:
            #     title = title.split(' - ', 1)[1]

            # Get episode number
            m = re.search(
                r'/\d+/(\d+)/\d+/',  # season/episode/show_id
                td.select('a')[0].attrs['href'])
            ep = m.group(1)
            curr_ep = ep
            curr_title = title

            # print("Got episode {} header: {}".format(ep, title))

        # Version header
        elif td.attrs.get('colspan', '') == '3':
            curr_version = td.text.strip()
            if ' ' in curr_version:
                curr_version = curr_version.split(' ', 1)[1]

            # print("  Version:", curr_version)

        elif 'language' in td.attrs.get('class', []):
            language = td.text.strip()

            completed_node = td.findNextSibling('td')
            completed = completed_node.text.strip().lower() == 'completado'
            if completed is False:
                continue

            link_node = completed_node.findNextSibling('td').select('a')[0]

            try:
                href = 'http:' + link_node.attrs['href']
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


class Fetcher(object):
    def __init__(self, headers={}):
        default_headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; WOW64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/50.0.2661.102 Safari/537.36'),
            'Accept-Language': 'en, en-gb;q=0.9, en-us;q=0.9',
            'Referer': ''
        }

        self._session = requests.Session()
        self._session.headers.update(default_headers)
        self._session.headers.update(headers)

    def fetch(self, url, headers={}):
        if not _NETWORK_ENABLED:
            raise RuntimeError('Network not enabled')

        resp = self._session.get(url, verify=False, headers=headers)
        if resp.status_code != 200:
            raise Exception('Invalid response')

        self._session.headers.update({'Referer': url})

        return resp.text

    def get_state(self):
        return {
            'headers': dict(self._session.headers),
            'cookies': self._session.cookies.get_dict()
        }

    def set_state(self, state):
        self._session.headers.clear()
        self._session.headers.update(state.get('headers', {}))

        self._session.cookies.clear()
        for (k, v) in state.get('cookies', {}).items():
            self._session.cookies.set(k, v)


def main(filename):
    api = API()
    subs = api.get_subtitles_from_filename(path.basename(filename))
    print(api.fetch_subtitle(subs[0]))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: {} filename".format(sys.argv[0]))
        sys.exit(1)

    main(sys.argv[1])
