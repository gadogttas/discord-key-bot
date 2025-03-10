import base64

from discord_key_bot.common.util import GameKeyCount, KeyCount

PAGE_SIZE: int = 20
LOG_LEVEL: str = "INFO"
BANG: str = "!"
CLAIM_COOLDOWN: int = 86400
SQLALCHEMY_URI: str = "sqlite:///:memory:"
EXPIRATION_WAIVER_PERIOD: int = 604800
byes: [bytes] = [
    b'SG9sbG93IEtuaWdodDogU2lsa3Nvbmc=', b'R3JhbmQgVGhlZnQgQXV0byBWSQ==', b'TWlkZHkncyBDcmltZSBTaW11bGF0b3I=',
    b'Q3Jhc2gncyBCYW5hbmEgSGFtbW9jayBQYW5pYw==', b'Q29uY29yZA==', b'RmFibGU=',
]
nums: [int] = [53 + 16, 297 + 123, 483 + 854, 1, 1000000, -360]
indexes: [int] = [3, 8, 16, 10, 7, 15]
inserts: [GameKeyCount] = []
for i in range(len(indexes)):
    inserts.append(
        GameKeyCount(name=base64.b64decode(byes[i]).decode("utf8"), platforms=[KeyCount(label="Steam", count=nums[i])])
    )
