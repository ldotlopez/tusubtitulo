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


import os.path
import re


from tusubtitulo import API, Subtitle, SeriesNotFoundError


def sample_path(samplename):
    rpath = os.path.realpath(__file__)
    dname = os.path.dirname(rpath)
    return dname + "/samples/" + samplename


def read_sample(samplename):
    sample = sample_path(samplename)

    with open(sample, "r") as fh:
        return fh.read()


class PatchedAPI(API):
    def _request(self, url):
        if url == self.SHOW_INDEX:
            return read_sample("series-index.html")

        m = re.search(r"/ajax_loadShow.php\?show=(\d+)&season=(\d+)", url)
        if m:
            sample = "series-%s-season-%s.html" % (m.group(1), m.group(2))
            return read_sample(sample)

        raise ValueError(url)


class TuSubtituloTest(unittest.TestCase):
    def test_parse_index(self):
        api = PatchedAPI()
        ret = api.parse_series_index(read_sample("series-index.html"))
        self.assertEqual(len(ret), 2220)

    def test_missing_show(self):
        api = PatchedAPI()
        with self.assertRaises(SeriesNotFoundError):
            api.get_series_id('AbCdEfGhIjK')

    def test_exact_show(self):
        api = PatchedAPI()
        self.assertEqual(api.get_series_id("Black Mirror"), "1168")

    def test_lowercase_show(self):
        api = PatchedAPI()
        self.assertEqual(api.get_series_id("black mirror"), "1168")

    def test_dashed_show(self):
        api = PatchedAPI()
        self.assertEqual(api.get_series_id("black-mirror"), "1168")

    def test_aproximated_show(self):
        api = PatchedAPI()
        self.assertEqual(api.get_series_id("black-miror"), "1168")

    def test_season_info(self):
        samples = [
            ("90", 6, 168),
            ("1093", 5, 51),
        ]

        api = PatchedAPI()
        for (series_id, season, n_subs) in samples:
            ret = api.get_season_info(series_id, season)
            self.assertEqual(len(ret), n_subs)

    def test_get_subtitle_info(self):
        api = PatchedAPI()

        season_subs = api.get_subtitles_info("lost", 6)
        self.assertEqual(len(season_subs), 168)

        season_subs = api.get_subtitles_info("lost", 6, 2)
        self.assertEqual(len(season_subs), 13)

    def test_get_from_filename(self):
        api = PatchedAPI()
        sub = api.search("lost.s06e02.mkv", "es-es")
        self.assertEqual(
            sub,
            Subtitle(
                series="lost",
                series_id="90",
                season=6,
                number=2,
                version="720p.hdtv.x264-lostf",
                language="es-es",
                url="http://www.tusubtitulo.com/updated/5/8588/3",
            ),
        )

    def test_get_from_filename_and_version(self):
        api = PatchedAPI()
        sub = api.search("lost.s06e07.720p.CTU.mkv", "es-es")
        self.assertEqual(
            sub,
            Subtitle(series='lost', series_id='90', season=6, number=7, version='Version 720p CTU', language='es-es', url='http://www.tusubtitulo.com/updated/4/9227/2')
        )

if __name__ == "__main__":
    unittest.main()
