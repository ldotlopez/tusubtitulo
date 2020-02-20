#!/usr/bin/env python3
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


import unittest
from unittest.mock import patch
import re
from os import path




def sample_path(samplename):
    rpath = path.realpath(__file__)
    dname = path.dirname(rpath)
    return dname + "/samples/" + samplename


def read_sample(samplename):
    sample = sample_path(samplename)

    with open(sample, "r") as fh:
        return fh.read()


import bs4
import urllib
import difflib
import functools


class API:
    SHOW_INDEX = "https://www.tusubtituloaaa.com/series.php"
    SEASON_INFO = "https://www.tusubtitulo.com/ajax_loadShow.php?show=%(series_id)s&season=%(season)s"

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; WOW64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/50.0.2661.102 Safari/537.36"
            ),
            "Accept-Language": "en, en-gb;q=0.9, en-us;q=0.9",
            "Accept-Charset": "utf-8, iso-8859-1;q=0.5",
            "Referer": ""
        }

    @functools.lru_cache()
    def get_series_id(self, show):
        buff = self.request(self.SHOW_INDEX)
        data = self.parse_index(buff)
        try:
            return data[show]
        except KeyError:
            pass

        try:
            return {
                k.lower(): v for (k, v) in data.items()
            }[show.lower()]
        except KeyError:
            pass

        ratios = [
            (key, difflib.SequenceMatcher(None, show.lower(), key.lower()).ratio())
            for key in data
        ]
        ratios = list(reversed(sorted(ratios, key=lambda x: x[1])))

        if ratios[0][1] > 0.8:
            return data[ratios[0][0]]

        raise ShowNotFoundError()

    def get_season_info(self, series_id, season):
        url = self.SEASON_INFO % dict(series_id=str(series_id), season=str(season))
        buff = self.request(url)
        return self.parse_season_info(buff)

    @functools.lru_cache()
    def parse_index(self, buff):
        soup = self._soupify(buff)
        return {
            x.text: x.attrs["href"].split('/')[-1]
            for x in soup.select("a")
            if x.attrs.get("href", "").startswith("/show/")
        }

    def request(self, url):
        ret = self._request(url)
        self.headers['Referer'] = url
        return ret

    @functools.lru_cache()
    def _request(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as fh:
            return fh.read()

    @functools.lru_cache()
    def _soupify(self, buff):
        return bs4.BeautifulSoup(buff, features="html.parser")


class ShowNotFoundError(Exception):
    pass


class TuSubtituloTest(unittest.TestCase):
    def test_parse_index(self):
        api = API()
        ret = api.parse_index(read_sample('series-index.html'))
        self.assertEqual(len(ret), 2220)

    def test_show_info(self):
        api = API()
        with patch.object(api, '_request', return_value=read_sample('series-index.html')) as mock:
            self.assertEqual(api.get_series_id('Black Mirror'), '1168')
            self.assertEqual(api.get_series_id('black mirror'), '1168')
            self.assertEqual(api.get_series_id('black-mirror'), '1168')
            self.assertEqual(api.get_series_id('black-miror'), '1168')

    def test_season_info(self):
        api = API()
        with patch.object(api, '_request', return_value=read_sample('series-1093-season-5.html')) as mock:
            api.get_season_info('1093', '5')


if __name__ == "__main__":
    unittest.main()
