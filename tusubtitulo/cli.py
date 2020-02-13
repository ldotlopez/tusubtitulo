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


import argparse
import sys
from os import path

import tusubtitulo


def download_for(filename, languages=None):
    extension_table = {"en-us": "en", "es-es": "es", "es-lat": "lat"}

    api = tusubtitulo.API()

    subs = {}

    for sub in api.get_subtitles_from_filename(path.basename(filename)):
        if sub.language not in subs:
            subs[sub.language] = []
        subs[sub.language].append(sub)

    for (language, subs) in subs.items():
        if languages and language not in languages:
            continue

        # Try to download proper version
        versions = [sub.version.lower() for sub in subs]
        propers = ["proper" in ver or "repack" in ver for ver in versions]
        try:
            match = subs[propers.index(True)]
        except ValueError:
            match = sorted(subs, key=lambda x: x.url)[-1]

        name, ext = path.splitext(filename)
        subname = "%(name)s.%(language)s.srt" % dict(
            name=name, language=extension_table[match.language]
        )

        if not path.exists(subname):
            with open(subname, "wb+") as fh:
                buff = api.fetch_subtitle(match)
                fh.write(buff)

            msg = "Saved %(language)s subtitle to %(subtitle_name)s"
            msg = msg % dict(language=match.language, subtitle_name=subname)
            print(msg)

        else:
            msg = (
                "Skipping %(language)s ,"
                "filename %(subtitle_name)s already exists"
            )
            msg = msg % dict(language=match.language, subtitle_name=subname)
            print(msg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--language",
        dest="languages",
        action="append",
        default=[],
        type=str,
    )
    parser.add_argument(dest="filenames", nargs="+")
    args = parser.parse_args(sys.argv[1:])

    if not args.filenames:
        args.print_help()
        sys.exit(1)

    for x in args.filenames:
        try:
            download_for(x, languages=[x.lower() for x in args.languages])

        except tusubtitulo.ParseError as e:
            msg = "Unable to parse '%(filename)s': %(error)s"
            msg = msg % dict(filename=x, error=str(e))
            print(msg, file=sys.stderr)

        except tusubtitulo.ShowNotFoundError as e:
            msg = "Show not found: %(show)s"
            msg = msg % dict(show=e.show)
            print(msg, file=sys.stderr)
