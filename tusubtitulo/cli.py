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
import os.path
import sys
import logging
import tusubtitulo
from tusubtitulo.parsers import LANG_CODES


LOG_LEVELS = [
    logging.CRITICAL,
    logging.ERROR,
    logging.WARNING,
    logging.INFO,
    logging.DEBUG,
]


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l", "--language", dest="languages", action="append", required=True
    )
    parser.add_argument("-f", "--force", dest="overwrite", action="store_true")
    parser.add_argument(
        "-q", "--quiet", dest="quiet", action="count", default=0,
    )
    parser.add_argument(
        "-v", "--verbose", dest="verbose", action="count", default=0,
    )

    parser.add_argument("files", nargs="+")
    args = parser.parse_args(argv)

    loglevel = min(max(0, 2 + args.verbose - args.quiet), len(LOG_LEVELS) - 1)
    logging.basicConfig()
    logger = logging.getLogger("tusubtitulo")
    logger.setLevel(LOG_LEVELS[loglevel])

    langcodes = list(LANG_CODES.values())
    for lang in args.languages:
        if lang not in langcodes:
            msg = "Unknow language. Valid values are: %(languages)s"
            msg = msg % dict(languages=', '.join(langcodes))
            logger.error(msg)
            sys.exit(255)

    api = tusubtitulo.API(logger=logger.getChild("api"))
    logger = logger.getChild("cli")

    for f in args.files:
        for lang in args.languages:
            output = subtitle_filename(f, lang)
            if os.path.exists(output) and not args.overwrite:
                msg = (
                    "%(filename)s: Destination filename '%(output)s' already "
                    "exists, skip"
                )
                msg = msg % dict(filename=f, output=output)
                logger.error(msg)
                continue

            try:
                subs = api.search_from_filename(f, language=lang)

            except tusubtitulo.InvalidFilename as e:
                msg = "%(filename)s: Invalid filename (%(error)s)"
                msg = msg % dict(filename=f, error=e)
                logger.error(msg)
                break

            except tusubtitulo.SeriesNotFoundError:
                msg = "%(filename)s: Series not found"
                msg = msg % dict(filename=f)
                logger.error(msg)
                break

            except tusubtitulo.NoSubtitlesFoundError:
                msg = (
                    "%(filename)s: No subtitles found for language "
                    "%(language)s"
                )
                msg = msg % dict(filename=f, language=lang)
                logger.error(msg)
                continue

            buff = api.download(subs[0])
            with open(output, "wb") as fh:
                fh.write(buff)

            msg = (
                "%(filename)s: subtitles for %(language)s saved to "
                "%(output)s"
            )
            msg = dict(filename=f, output=output)
            logger.info(msg)


def subtitle_filename(f, language):
    return "%s.%s.srt" % (".".join(f.split(".")[:-1]), language)


if __name__ == "__main__":
    main(sys.argv[1:])
