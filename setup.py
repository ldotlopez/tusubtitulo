#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from os import path
from datetime import datetime
from setuptools import setup


with open(path.dirname(path.realpath(__file__)) + "/requirements.txt") as fh:
    pkgs = fh.readlines()

pkgs = [x.strip() for x in pkgs]
pkgs = [x for x in pkgs if x and x[0] != "#"]

version = "0.0." + datetime.now().strftime("%Y%m%d%H%M%S")

setup(
    name="tusubtitulo",
    version=version,
    author="Luis López",
    author_email="luis@cuarentaydos.com",
    packages=["tusubtitulo"],
    entry_points={"console_scripts": ["tusubtitulo = tusubtitulo.cli:main",],},
    url="https://github.com/ldotlopez/tusubtitulo",
    license="LICENSE.txt",
    description="API and command line downloader for tusubtitulo.com",
    long_description=open("README.md").read(),
    install_requires=pkgs,
)
