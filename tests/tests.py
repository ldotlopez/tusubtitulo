#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals, print_function


import unittest
from os import path
import re

import tusubtitulo
tusubtitulo._NETWORK_ENABLED = False


def sample_path(samplename):
    rpath = path.realpath(__file__)
    dname = path.dirname(rpath)
    return dname + '/samples/' + samplename


def read_sample(samplename):
    sample = sample_path(samplename)

    with open(sample, 'rb') as fh:
        return fh.read()


def mock_fetcher(url, headers=None):
    url = re.subn(
        r'[^0-9a-z]',
        '-',
        url, flags=re.IGNORECASE)[0]
    return read_sample(url)


class API(tusubtitulo.API):
    def __init__(self, *args, **kwargs):
        super(API, self).__init__(fetch_func=mock_fetcher)


class ParsersTest(unittest.TestCase):
    def test_series_index_parser(self):

        data = tusubtitulo.parse_index_page(
            mock_fetcher(tusubtitulo.SERIES_INDEX_URL),
            asdict=True
        )

        self.assertEqual(
            data['Black Mirror'],
            'https://www.tusubtitulo.com/show/1168'
        )

    def test_season_page_parser(self):
        url = tusubtitulo.SEASON_PAGE_PATTERN.format(show='1093', season='5')
        data = tusubtitulo.parse_season_page(mock_fetcher(url))

        self.assertTrue((
            '10',
            'She Gets Revenge',
            'WEB-DL',
            'Español (España)',
            'https://www.tusubtitulo.com/updated/5/47505/1') in data)


class APITest(unittest.TestCase):
    def setUp(self):
        self.api = API()

    def test_exact_match(self):
        info = self.api.get_show('Black Mirror')
        self.assertEqual(info.id, '1168')
        self.assertEqual(
            info.url,
            tusubtitulo.SERIES_PAGE_PATTERN.format(show='1168'))

    def test_lowercase_match(self):
        info = self.api.get_show('z nation')
        self.assertEqual(info.id, '2201')
        self.assertEqual(info.title, 'Z Nation')

    def test_lowercase_similar_1(self):
        info = self.api.get_show('hawaii five 0')
        self.assertEqual(info.id, '695')

    def test_lowercase_similar_2(self):
        info = self.api.get_show('mad man')
        self.assertEqual(info.id, '79')
        self.assertEqual(info.title, 'Mad Men')

    def test_missing_series(self):
        with self.assertRaises(tusubtitulo.ShowNotFoundError):
            self.api.get_show('foo')

    def test_subtitles_info(self):
        info = self.api.get_subtitles('American Horror Story', '5', '3')
        self.assertEqual(len(info), 5)

        es_ES = [x for x in info if x.language == 'es-ES']
        self.assertEqual(len(es_ES), 3)

    def test_from_filename(self):
        info = self.api.get_subtitles_from_filename(
            'American Horror Story 5x03 - Mommy.mkv')
        self.assertEqual(len(info), 5)

        es_ES = [x for x in info if x.language == 'es-ES']
        self.assertEqual(len(es_ES), 3)


if __name__ == '__main__':
    unittest.main()
