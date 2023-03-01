import json
import replus as rp

cost: str = ""
colors: list = []
cmc: float = 0.0
colorless: bool = False
monocolored: bool = False
multicolored: bool = False
hybrid: bool = False
phyrexian: bool = False


def __init__(self, mana_json: str | dict):

    if isinstance(mana_json, str):
        mana_json = json.loads(mana_json)

    for key, value in mana_json.items():
        if hasattr(self, key):
            setattr(self, key, value)

@property
def hybrid(self) -> bool:
    return True if rp.search("/\{[WUBRG2]/[WUBRG](\/P)?\}/i", self.cost) else False


@property
def phyrexian(self) -> bool:
    return True if rp.search("/[WUBRG2]/P\}/i", self.cost) else False
