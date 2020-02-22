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
import urllib.request


import bs4
import guessit

from . import parsers


class API:
    ROOT_URL = "https://www.tusubtitulo.com/"
    SHOW_INDEX = ROOT_URL + "series.php"
    SEASON_INFO = (
        ROOT_URL + "ajax_loadShow.php?show=%(series_id)s&season=%(season)s"
    )

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("tusubtitulo")
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; WOW64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/50.0.2661.102 Safari/537.36"
            ),
            "Accept-Language": "en, en-gb;q=0.9, en-us;q=0.9",
            "Accept-Charset": "utf-8, iso-8859-1;q=0.5",
        }

    def search(
        self,
        series: str,
        season: int,
        number: int = None,
        language: str = None,
    ):
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

        if language:
            subtitles = [x for x in subtitles if x.language == language]

        return subtitles

    def search_from_filename(self, filepath, language):
        info = guessit.guessit(filepath)

        if info.get("type") != "episode":
            excmsg = "Detected file type is: %(type)s, expected 'episode'"
            excmsg = excmsg % dict(type=info.get("type", "unknow"))
            raise InvalidFilename(excmsg)

        for req in ["title", "season", "episode"]:
            if not info.get(req, ""):
                excmsg = "Missing required info for '%(field)s'"
                excmsg = excmsg % dict(field=req)
                raise InvalidFilename(excmsg)

        subtitles = self.search(
            info["title"], info["season"], info["episode"], language=language
        )
        if not subtitles:
            raise NoSubtitlesFoundError()

        subtitles = list(
            reversed(
                sorted(subtitles, key=lambda x: distance(x.version, filepath))
            )
        )

        return subtitles

    def download(self, subtitle):
        referer = self.SEASON_INFO % dict(
            series_id=subtitle.series_id, season=subtitle.season
        )
        buff = self.request(subtitle.url, referer=referer)
        return buff

    def get_series_id(self, series: str):
        buff = self.request(self.SHOW_INDEX, referer=self.ROOT_URL)
        data = parsers.series_index(buff)

        msg = "Got %(n_items)s series from index"
        msg = msg % dict(n_items=len(data))
        self.logger.debug(msg)

        # Return exact match
        try:
            ret = data[series]
            msg = "Got exact match for %(series)s"
            msg = msg % dict(series=series)
            self.logger.debug(msg)
            return ret
        except KeyError:
            pass

        # Return lowercase match
        try:
            ret = {k.lower(): v for (k, v) in data.items()}[series.lower()]

            msg = "Got case-independent match for %(series)s"
            msg = msg % dict(series=series)
            self.logger.debug(msg)

            return ret

        except KeyError:
            pass

        # Return by string-distance
        ratios = [(key, distance(series.lower(), key.lower())) for key in data]
        ratios = list(reversed(sorted(ratios, key=lambda x: x[1])))

        if ratios[0][1] > 0.8:
            msg = (
                "Got aproximated match for %(series)s: %(match)s "
                "(q=%(ratio)s)"
            )
            msg = msg % dict(
                series=series, match=ratios[0][0], ratio=ratios[0][1]
            )
            self.logger.debug(msg)
            return data[ratios[0][0]]

        raise SeriesNotFoundError()

    def get_season_info(self, series_id, season):
        url = self.SEASON_INFO % dict(
            series_id=str(series_id), season=str(season)
        )
        buff = self.request(url, referer=self.SHOW_INDEX)
        data = parsers.season_index(buff)

        msg = (
            "Got %(n_items)s for series id '%(series_id)s' "
            "and season %(season)s"
        )
        msg = msg % dict(n_items=len(data), series_id=series_id, season=season)

        return data

    def request(self, url, referer=None):
        headers = {}
        headers.update(self.headers)
        if referer:
            headers.update({"Referer": referer})

        return self._request(url, headers)

    def _request(self, url, headers=None):
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req) as fh:
            buff = fh.read()

        msg = "Request '%(url)s got %(bytes)s bytes' (referer: %(referer)s)"
        msg = msg % dict(
            url=url, bytes=len(buff), referer=headers.get("Referer", "")
        )
        self.logger.debug(msg)

        return buff

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


def distance(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


class SeriesNotFoundError(Exception):
    pass


class EpisodeNotFoundError(Exception):
    pass


class NoSubtitlesFoundError(Exception):
    pass


class InvalidFilename(Exception):
    pass
