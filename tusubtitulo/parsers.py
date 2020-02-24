import re
import sys
import bs4

LANG_CODES = {
    "english": "en-us",
    "english (us)": "en-us",
    "español": "es-es",
    "español (españa)": "es-es",
    "español (latinoamérica)": "es-lat",
    "català": "es-ca",
    "galego": "es-gl",
    "brazilian": "pt-br",
}


def series_index(buff):
    soup = bs4.BeautifulSoup(buff, features="html.parser")
    ret = {
        x.text: x.attrs["href"].split("/")[-1]
        for x in soup.select("a")
        if x.attrs.get("href", "").startswith("/show/")
    }

    if not len(ret):
        raise ParseError()

    return ret


def season_index(buff):
    def _find_episode_block(x):
        while True:
            if x.parent is None:
                raise ValueError()

            if x.name == "table":
                return x

            x = x.parent

    def _get_episode_number(x):
        m = re.search(r"/episodes/\d+/.+?-\d+x(\d+)", x.attrs.get("href", ""))
        if not m:
            raise ValueError()

        return int(m.group(1))

    soup = bs4.BeautifulSoup(buff, features="html.parser")
    blocks = [
        (_get_episode_number(x), _find_episode_block(x))
        for x in soup.select('a[href*="/episodes/"]')
    ]

    ret = []
    for (ep_number, el) in blocks:
        version_g = (x for x in range(sys.maxsize))
        cur_version = None
        cur_lang = None
        cur_link = None

        for line in el.select("tr"):
            # Get version
            m = re.search(r"Versi.+?n(.+)?", line.text, re.IGNORECASE)
            if m:
                cur_version = m.group(1).strip() or (
                    "ver-%s" % next(version_g)
                )

            # Match language
            language = line.select_one("td.language")
            if language:
                try:
                    cur_lang = LANG_CODES[language.text.strip().lower()]
                except KeyError:
                    continue  # Log

            # Match download link
            link = line.select_one("a")
            if language and link:
                cur_link = link.attrs["href"]
                ret.append(
                    (ep_number, cur_version, cur_lang, "http:" + cur_link)
                )

    return ret


class ParseError(Exception):
    pass
