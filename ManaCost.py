import json
import replus as rp


class ManaCost:
    cost: str = ""
    _colors: list = []
    cmc: float = 0.0
    colorless: bool = False
    monocolored: bool = False
    multicolored: bool = False

    def __init__(self, mana_json: str | dict):
        if isinstance(mana_json, str):
            mana_json = json.loads(mana_json)

        for key, value in mana_json.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def includes(self, type_name: str) -> bool:
        return self.types.get(type_name.strip(), False)

    def excludes(self, type_name: str) -> bool:
        return not self.includes(type_name)

    @property
    def colors(self) -> list:
        return self._colors

    @colors.setter
    def colors(self, colors: list) -> None:
        self._colors = self._color_filter(colors)

    def _color_filter(self, colors: list) -> list:
        if 0 < len(colors):
            colors.sort(key=lambda c: ['W', 'U', 'B', 'R', 'G'].index(c))
        return colors

    @property
    def string(self) -> str:
        return "".join(self.colors)

    @property
    def count(self) -> int:
        return len(self.colors)

    @property
    def hybrid(self) -> bool:
        return True if rp.search("/\{[WUBRG2]/[WUBRG](\/P)?\}/i", self.cost) else False

    @property
    def phyrexian(self) -> bool:
        return True if rp.search("/[WUBRG2]/P\}/i", self.cost) else False
