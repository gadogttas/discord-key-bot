import re

keyspace = {
    "gog": [
        r"^[a-z,A-Z,0-9]{5}-[a-z,A-Z,0-9]{5}-[a-z,A-Z,0-9]{5}-[a-z,A-Z,0-9]{5}$",
        r"^[a-z,A-Z,0-9]{18}$"
    ],
    "steam": [
        r"^[a-z,A-Z,0-9]{5}-[a-z,A-Z,0-9]{5}-[a-z,A-Z,0-9]{5}$",
        r"^[a-z,A-Z,0-9]{5}-[a-z,A-Z,0-9]{5}-[a-z,A-Z,0-9]{5}-[a-z,A-Z,0-9]{5}-[a-z,A-Z,0-9]{5}$",
    ],
    "playstation": [r"^[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}$"],
    "origin": [
        r"^[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}$"
    ],
    "uplay": [
        r"^[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}$",
        r"^[a-z,A-Z,0-9]{3}-[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}-[a-z,A-Z,0-9]{4}$",
    ],
    "switch": [r"^[a-z,A-Z,0-9]{16}$"],
    "xbox": [r"^[a-z,A-Z,0-9]{25}$"],
}

examples = {
    "GOG": ["AAAAA-BBBBB-CCCCC-DDDDD", "ABCDEABCDEABCDEABC (18 chars)"],
    "Steam": ["AAAAA-BBBBB-CCCCC", "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE"],
    "Playstation": ["AAAA-BBBB-CCCC"],
    "Origin": ["AAAA-BBBB-CCCC-DDDD-EEEE"],
    "Switch": ["ABCDABCDABCDABCD (16 chars)"],
    "Xbox": ["ABCDEABCDEABCDEABCDEABCDE (25 chars)"],
}

_compiled = {k: [re.compile(r) for r in v] for k, v in keyspace.items()}


def parse_name(pretty_name):
    name = re.sub(r"\W", "_", pretty_name.lower())
    return name


def parse_key(key):
    for k, v in _compiled.items():
        for r in v:
            if r.match(key):
                return k, key

    return False, "Bad key format!"
