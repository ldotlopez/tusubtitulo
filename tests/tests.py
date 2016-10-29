#!/usr/bin/env python3

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

    with open(sample, 'rb') as fh:
        return fh.read()


def sample_fetcher(url, headers=None):
    url = re.subn(
        r'[^0-9a-z]',
        '-',
        url, flags=re.IGNORECASE)[0]
    return read_sample(url)


class TestShowInfo(tusubtitulo.ShowInfo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, fetch=sample_fetcher)


class TuSubtituloTest(unittest.TestCase):
    def test_series_finder_exact(self):
        info = TestShowInfo('Black Mirror')
        self.assertEqual(info.id, '1168')

    def test_series_finder_lower(self):
        info = TestShowInfo('z nation')
        self.assertEqual(info.id, '2201')

    def test_series_finder_similar_1(self):
        info = TestShowInfo('Hawaii Five 0')
        self.assertEqual(info.id, '695')

    def test_series_finder_similar_2(self):
        info = TestShowInfo('mad man')
        self.assertEqual(info.id, '79')

    def test_season_info(self):
        info = TestShowInfo('American Horror Story', id='1093')
        subs = info.get_season_subtitles(5)
        print(repr(subs))

if __name__ == '__main__':
    unittest.main()
