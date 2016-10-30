#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals, print_function


import unittest
import re
from os import path

import tusubtitulo
tusubtitulo._NETWORK_ENABLED = False


def sample_path(samplename):
    rpath = path.realpath(__file__)
    dname = path.dirname(rpath)
    return dname + '/samples/' + samplename


def read_sample(samplename):
    sample = sample_path(samplename)

    with open(sample, 'r') as fh:
        return fh.read()


class MockFetcher(object):
    state = {
        'headers': {
            'foo': 'bar'
        },
        'cookies': {
            'qwerty': '123456'
        }
    }

    def fetch(self, url, headers={}):
        url = re.subn(
            r'[^0-9a-z]',
            '-',
            url, flags=re.IGNORECASE)[0]
        return read_sample(url)

    def get_state(self):
        return self.state.copy()

    def set_state(self, state):
        self.state = state.copy()


class API(tusubtitulo.API):
    def __init__(self, *args, **kwargs):
        super(API, self).__init__(fetcher=MockFetcher())


class ParsersTest(unittest.TestCase):
    fetcher = MockFetcher()

    def test_series_index_parser(self):

        data = tusubtitulo.parse_index_page(
            self.fetcher.fetch(tusubtitulo.SERIES_INDEX_URL))

        self.assertEqual(
            data['Black Mirror'],
            'https://www.tusubtitulo.com/show/1168'
        )

    def test_season_page_parser(self):
        url = tusubtitulo.SEASON_PAGE_PATTERN.format(show='1093', season='5')
        data = tusubtitulo.parse_season_page(self.fetcher.fetch(url))

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

        es_ES = [x for x in info if x.language == 'es-es']
        self.assertEqual(len(es_ES), 3)

    def test_from_filename(self):
        info = self.api.get_subtitles_from_filename(
            'American Horror Story 5x03 - Mommy.mkv')
        self.assertEqual(len(info), 5)

        es_ES = [x for x in info if x.language == 'es-es']
        self.assertEqual(len(es_ES), 3)

    def test_house_5_03(self):
        info = self.api.get_subtitles_from_filename('house 5x03.avi')
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0].version, 'HDTV.XviD-LOL')
        self.assertEqual(info[0].language, 'es-es')
        self.assertEqual(
            info[0].url, 'https://www.tusubtitulo.com/updated/5/40/0')


class FetcherTest(unittest.TestCase):
    def setUp(self):
        tusubtitulo._NETWORK_ENABLED = True

    def tearDown(self):
        tusubtitulo._NETWORK_ENABLED = False

    def test_dump(self):
        fetcher = tusubtitulo.Fetcher()
        fetcher.fetch('http://httpbin.org/cookies/set?foo=bar')

        state = fetcher.get_state()
        self.assertEqual(state['cookies']['foo'], 'bar')
        self.assertEqual(
            state['headers']['Referer'],
            'http://httpbin.org/cookies/set?foo=bar')

    def test_load(self):
        state = {
            'headers': {
                'Referer': 'http://localhost/',
                'X-Foo': 'foo'
                # No user-agent here!
            },
            'cookies': {
                'salchi': 'papa'
            }
        }
        fetcher = tusubtitulo.Fetcher()
        fetcher.set_state(state)

        self.assertFalse('User-Agent' in fetcher._session.headers)
        self.assertEqual(fetcher._session.headers['X-Foo'], 'foo')


if __name__ == '__main__':
    unittest.main()
