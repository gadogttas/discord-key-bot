import re
from typing import List, Dict, Iterable


class Platform(object):
    """Class representing a platform"""

    def __init__(
        self, name: str, key_regexes: List[str], example_keys: List[str]
    ) -> None:
        self.name: str = name
        self.search_name: str = name.lower()
        self._patterns: List[re.Pattern] = self._compile_patterns(key_regexes)
        self.example_keys = example_keys

    def __str__(self) -> str:
        return self.name

    def is_valid_key(self, key: str) -> bool:
        return any(pattern.match(key) for pattern in self._patterns)

    @staticmethod
    def _compile_patterns(patterns: List[str]) -> List[re.Pattern]:
        return [re.compile(pattern) for pattern in patterns]


gog: Platform = Platform(
    name="GOG",
    key_regexes=[
        r"^[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}$",
        r"^[a-zA-Z0-9]{18}$",
    ],
    example_keys=["AAAAA-BBBBB-CCCCC-DDDDD", "ABCDEABCDEABCDEABC (18 chars)"],
)

steam: Platform = Platform(
    name="Steam",
    key_regexes=[
        r"^[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}$",
        r"^[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}$",
        r"^[a-zA-Z0-9]{25}$",
    ],
    example_keys=["AAAAA-BBBBB-CCCCC", "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE", "ABCDEABCDEABCDEABCDEABCDE (25 chars)"],
)

playstation: Platform = Platform(
    name="PlayStation",
    key_regexes=[r"^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$"],
    example_keys=["AAAA-BBBB-CCCC"],
)

origin: Platform = Platform(
    name="Origin",
    key_regexes=[
        r"^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$"
    ],
    example_keys=["AAAA-BBBB-CCCC-DDDD-EEEE"],
)

uplay: Platform = Platform(
    name="UPlay",
    key_regexes=[
        r"^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$",
        r"^[a-zA-Z0-9]{3}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$",
    ],
    example_keys=["AAAA-BBBB-CCCC-DDDD", "AAA-BBBB-CCCC-DDDD-EEEE"],
)

xbox: Platform = Platform(
    name="Xbox",
    key_regexes=[
        r"^[a-zA-Z0-9]{25}$",
        r"^[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}$"
    ],
    example_keys=["ABCDEABCDEABCDEABCDEABCDE (25 chars)", "ABCDE-ABCDE-ABCDE-ABCDE-ABCDE"],
)

windows: Platform = Platform(
    name="Windows",
    key_regexes=[
        r"^[a-zA-Z0-9]{25}$",
        r"^[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{5}$"
    ],
    example_keys=["ABCDEABCDEABCDEABCDEABCDE (25 chars)", "ABCDE-ABCDE-ABCDE-ABCDE-ABCDE"],
)

switch: Platform = Platform(
    name="Switch",
    key_regexes=[r"^[a-zA-Z0-9]{16}$"],
    example_keys=["ABCDABCDABCDABCD (16 chars)"],
)

battleNet: Platform = Platform(
    name="Battle.net",
    key_regexes=[
        r"^[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{5}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}$"
    ],
    example_keys=["ABCD-ABCD-ABCDE-ABCD-ABCD"],
)


# TODO: should I make a registry class for these?
_all_platforms: Dict[str, Platform] = {
    gog.search_name: gog,
    steam.search_name: steam,
    playstation.search_name: playstation,
    origin.search_name: origin,
    uplay.search_name: uplay,
    xbox.search_name: xbox,
    switch.search_name: switch,
    windows.search_name: windows,
    battleNet.search_name: battleNet,
}


def all_platforms() -> Iterable[Platform]:
    return [platform for _, platform in sorted(_all_platforms.items())]


def get_platform(platform_name: str) -> Platform:
    try:
        return _all_platforms[platform_name.lower()]
    except KeyError:
        raise ValueError
