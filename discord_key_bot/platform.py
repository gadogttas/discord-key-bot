import re
from typing import List, Dict, Iterable


class PlatformNotFound(Exception):
    """Exception to be raised when a key platform cannot be inferred"""

    pass


class Platform(object):
    """Class representing a platform"""

    def __init__(self, name: str, key_regexes: List[str], example_keys: List[str]) -> None:
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
    ],
    example_keys=["AAAAA-BBBBB-CCCCC", "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE"],
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
    key_regexes=[r"^[a-zA-Z0-9]{25}$"],
    example_keys=["ABCDEABCDEABCDEABCDEABCDE (25 chars)"],
)

switch: Platform = Platform(
    name="Switch",
    key_regexes=[r"^[a-zA-Z0-9]{16}$"],
    example_keys=["ABCDABCDABCDABCD (16 chars)"],
)


# TODO: should I make a registry class for these?
all_platforms: Dict[str, Platform] = {
    gog.search_name: gog,
    steam.search_name: steam,
    playstation.search_name: playstation,
    origin.search_name: origin,
    uplay.search_name: uplay,
    xbox.search_name: xbox,
    switch.search_name: switch,
}


def infer_platform(key: str) -> Platform:
    for platform in all_platforms.values():
        if platform.is_valid_key(key):
            return platform

    raise PlatformNotFound


def pretty_platform(platform: str) -> str:
    """Find the properly capitalized platform name"""

    return all_platforms[platform.lower()].name


def pretty_platforms(platforms: Iterable[str]) -> str:
    """Deduplicate and properly capitalize the provided list of platform names"""

    return ", ".join(pretty_platform(platform) for platform in sorted(set(platforms)))
