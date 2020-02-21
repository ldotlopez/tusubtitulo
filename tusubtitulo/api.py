# -*- encoding: utf-8 -*-

# Copyright (C) 2019 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


import dataclasses
import difflib
import logging
import os.path
import re
import sys
import urllib


import bs4
import guessit

def distance(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


class API:
    SHOW_INDEX = "https://www.tusubtitulo.com/series.php"
    SEASON_INFO = "https://www.tusubtitulo.com/ajax_loadShow.php?show=%(series_id)s&season=%(season)s"

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger('tusubtitulo')
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; WOW64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/50.0.2661.102 Safari/537.36"
            ),
            "Accept-Language": "en, en-gb;q=0.9, en-us;q=0.9",
            "Accept-Charset": "utf-8, iso-8859-1;q=0.5",
            "Referer": "",
        }

    def search(self, filepath, language):
        info = guessit.guessit(filepath)

        if info.get("type") != "episode":
            excmsg = "Detected file type is: %(type)s, expected 'episode'"
            excmsg = excmsg % dict(type=info.get("type", "unknow"))
            raise InvalidFile(excmsg)

        for req in ["title", "season", "episode"]:
            if not info.get(req, ""):
                excmsg = "Missing required info for '%(field)'"
                excmsg = excmsg % dict(field=req)
                raise InvalidFile(excmsg)

        subtitles = self.get_subtitles_info(info["title"], info["season"], info["episode"])
        subtitles = [x for x in subtitles if x.language == language]
        subtitles = list(reversed(sorted(subtitles, key=lambda x: distance(x.version, filepath))))

        return subtitles[0]

    def get_subtitles_info(self, series: str, season: int, number: int = None):
        series_id = self.get_series_id(series)
        subtitles = [
            Subtitle(
                series=series,
                series_id=series_id,
                season=season,
                number=x[0],
                version=x[1],
                language=x[2],
                url=x[3],
            )
            for x in self.get_season_info(series_id, season)
        ]
        if number:
            subtitles = [x for x in subtitles if x.number == number]

        return subtitles

    def get_series_id(self, show: str):
        buff = self.request(self.SHOW_INDEX)
        data = self.parse_series_index(buff)

        # Return exact match
        try:
            return data[show]
        except KeyError:
            pass

        # Return lowercase match
        try:
            return {k.lower(): v for (k, v) in data.items()}[show.lower()]
        except KeyError:
            pass

        # Return by string-distance
        ratios = [
            (
                key,
                distance(show.lower(), key.lower())
            )
            for key in data
        ]
        ratios = list(reversed(sorted(ratios, key=lambda x: x[1])))

        if ratios[0][1] > 0.8:
            return data[ratios[0][0]]

        raise SeriesNotFoundError()

    def get_season_info(self, series_id, season):
        url = self.SEASON_INFO % dict(
            series_id=str(series_id), season=str(season)
        )
        buff = self.request(url)
        return self.parse_season_info(buff)

    def parse_series_index(self, buff):
        soup = self._soupify(buff)
        return {
            x.text: x.attrs["href"].split("/")[-1]
            for x in soup.select("a")
            if x.attrs.get("href", "").startswith("/show/")
        }

    def parse_season_info(self, buff):
        lang_codes = {
            "english": "en-us",
            "english (us)": "en-us",
            "español": "es-es",
            "español (españa)": "es-es",
            "español (latinoamérica)": "es-lat",
            "català": "es-ca",
            "galego": "es-gl",
            "brazilian": "pt-br",
        }

        def _find_episode_block(x):
            while True:
                if x.parent is None:
                    raise ValueError()

                if x.name == "table":
                    return x

                x = x.parent

        def _get_episode_number(x):
            m = re.search(
                r"/episodes/\d+/.+?-\d+x(\d+)", x.attrs.get("href", "")
            )
            if not m:
                raise ValueError()

            return int(m.group(1))

        soup = self._soupify(buff)
        blocks = [
            (_get_episode_number(x), _find_episode_block(x))
            for x in soup.select('a[href*="/episodes/"]')
        ]

        ret = []
        for (ep_number, el) in blocks:
            version_g = (x for x in range(sys.maxsize))
            cur_version = None
            cur_lang = None
            cur_link = None

            for line in el.select("tr"):
                # Get version
                m = re.search(r"Versi.+?n(.+)?", line.text, re.IGNORECASE)
                if m:
                    cur_version = m.group(1).strip() or (
                        "ver-%s" % next(version_g)
                    )

                # Match language
                language = line.select_one("td.language")
                if language:
                    try:
                        cur_lang = lang_codes[language.text.strip().lower()]
                    except KeyError:
                        continue  # Log

                # Match download link
                link = line.select_one("a")
                if language and link:
                    cur_link = link.attrs["href"]
                    ret.append(
                        (ep_number, cur_version, cur_lang, "http:" + cur_link)
                    )

        return ret

    def request(self, url):
        ret = self._request(url)
        self.headers["Referer"] = url
        return ret

    def _request(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as fh:
            return fh.read()

    def _soupify(self, buff):
        return bs4.BeautifulSoup(buff, features="html.parser")


@dataclasses.dataclass
class Subtitle:
    series: str
    series_id: str
    season: int
    number: int
    version: str
    language: str
    url: str


class SeriesNotFoundError(Exception):
    pass

class ParseError(Exception):
    pass
