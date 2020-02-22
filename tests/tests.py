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


from tusubtitulo import API, SeriesNotFoundError
from tusubtitulo.parsers import (
    series_index as parse_series_index,
    season_index as parse_season_index,
    ParseError,
)
from tusubtitulo.cli import subtitle_filename


def sample_path(samplename):
    rpath = os.path.realpath(__file__)
    dname = os.path.dirname(rpath)
    return dname + "/samples/" + samplename


def read_sample(samplename):
    sample = sample_path(samplename)

    with open(sample, "r") as fh:
        return fh.read()


def request_patch(url, headers=None):
    # print("=> %s (from: %s)" % (url, headers["Referer"]))
    if url == API.SHOW_INDEX:
        return read_sample("series-index.html")

    m = re.search(r"/ajax_loadShow.php\?show=(\d+)&season=(\d+)", url)
    if m:
        sample = "series-%s-season-%s.html" % (m.group(1), m.group(2))
        return read_sample(sample)

    if "tusubtitulo.com/updated" in url:
        return b"foo"

    raise ValueError(url)


class ParsersTest(unittest.TestCase):
    def test_parse_index(self):
        ret = parse_series_index(read_sample("series-index.html"))
        self.assertEqual(len(ret), 2220)

    def test_parse_index_error(self):
        with self.assertRaises(ParseError):
            parse_series_index("afasdfasdfasd")

    def test_parse_season(self):
        samples = [
            ("90", 6, 168),
            ("1093", 5, 51),
        ]
        for (series_id, season, expected) in samples:
            ret = parse_season_index(
                read_sample("series-%s-season-%d.html" % (series_id, season))
            )
            self.assertEqual(len(ret), expected)


class TuSubtituloTest(unittest.TestCase):
    def test_exact_show(self):
        api = API()
        with patch.object(api, "_request", side_effect=request_patch) as mock:
            self.assertEqual(api.get_series_id("Black Mirror"), "1168")
            self.assertMockCalls(
                mock,
                [
                    (
                        "https://www.tusubtitulo.com/series.php",
                        "https://www.tusubtitulo.com/",
                    )
                ],
            )

    def test_lowercase_show(self):
        api = API()
        with patch.object(api, "_request", side_effect=request_patch):
            self.assertEqual(api.get_series_id("black mirror"), "1168")

    def test_dashed_show(self):
        api = API()
        with patch.object(api, "_request", side_effect=request_patch):
            self.assertEqual(api.get_series_id("black-mirror"), "1168")

    def test_aproximated_show(self):
        api = API()
        with patch.object(api, "_request", side_effect=request_patch):
            self.assertEqual(api.get_series_id("black-miror"), "1168")

    def test_missing_show(self):
        api = API()
        with patch.object(api, "_request", side_effect=request_patch):
            with self.assertRaises(SeriesNotFoundError):
                api.get_series_id("AbCdEfGhIjK")

    def test_search(self):
        api = API()
        with patch.object(api, "_request", side_effect=request_patch) as mock:
            subs = api.search("lost", 6)
            self.assertEqual(len(subs), 168)
            self.assertMockCalls(
                mock,
                [
                    (
                        "https://www.tusubtitulo.com/series.php",
                        "https://www.tusubtitulo.com/",
                    ),
                    (
                        "https://www.tusubtitulo.com/ajax_loadShow.php?show=90&season=6",
                        "https://www.tusubtitulo.com/series.php",
                    ),
                ],
            )

    def test_search_from_filename(self):
        api = API()
        with patch.object(api, "_request", side_effect=request_patch) as mock:
            sub = api.search_from_filename(
                "lost.s06e07.720p.CTU.mkv", language="es-es"
            )
            self.assertMockCalls(
                mock,
                [
                    (
                        "https://www.tusubtitulo.com/series.php",
                        "https://www.tusubtitulo.com/",
                    ),
                    (
                        "https://www.tusubtitulo.com/ajax_loadShow.php?show=90&season=6",
                        "https://www.tusubtitulo.com/series.php",
                    ),
                ],
            )

    def test_download(self):
        api = API()
        with patch.object(api, "_request", side_effect=request_patch) as mock:
            sub = api.search_from_filename(
                "lost.s06e07.720p.CTU.mkv", language="es-es"
            )[0]

        self.assertEqual(
            sub.url, "http://www.tusubtitulo.com/updated/4/9227/2"
        )
        with patch.object(api, "_request", side_effect=request_patch) as mock:
            buff = api.download(sub)
            self.assertEqual(buff, b"foo")
            self.assertMockCalls(
                mock,
                [
                    (
                        "http://www.tusubtitulo.com/updated/4/9227/2",
                        "https://www.tusubtitulo.com/ajax_loadShow.php?show=90&season=6",
                    )
                ],
            )

    def assertMockCalls(self, mock, trace):
        self.assertEqual(len(trace), len(mock.call_args_list))

        for (trace_step, call_args) in zip(trace, mock.call_args_list):
            trace_url, trace_referer = trace_step
            call_url, call_headers = call_args[0]

            self.assertEqual(trace_url, call_url)
            self.assertEqual(trace_referer, call_headers["Referer"])


class CLITest(unittest.TestCase):
    def test_subtitle_filename(self):
        self.assertEqual(
            subtitle_filename("lost.s01.e02.mkv", language="es-es"),
            "lost.s01.e02.es-es.srt",
        )


if __name__ == "__main__":
    unittest.main()
