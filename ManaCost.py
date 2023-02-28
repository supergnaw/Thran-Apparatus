import replus as rp

_mana_cost: str = ""
colors: list = []
cmc: float = 0.0
colorless: bool = False
monocolored: bool = False
multicolored: bool = False
phyrexian: bool = False
hybrid: bool = False

def __init__(self, mana_cost: str = None):
    self.cost = mana_cost

def _color_filter(self):
    colors = list(set(rp.findall("/([WUBRG])/i", self.mana_cost)))
    colors.sort(key=lambda c: ['W', 'U', 'B', 'R', 'G'].index(c))
    self.colors = colors

@property
def mana_cost(self) -> str:
    return self._mana_cost

@mana_cost.setter
def cost(self, mana_cost: str) -> None:
    self._mana_cost = mana_cost
    self.colors = self._color_filter()

@property
def colors(self) -> list:
    pass

@property
def colors(self) -> float:
    pass

@property
def colorless(self) -> bool:
    return True if 0 == len(self.colors) else False

@property
def monocolored(self) -> bool:
    return True if 1 == len(self.colors) else False

@property
def multicolored(self) -> bool:
    return True if 1 < len(self.colors) else False

@property
def hybrid(self) -> bool:
    return True if rp.search("/\{[WUBRG2]/[WUBRG](\/P)?\}/i", self._mana_cost["cost"]) else False

@property
def phyrexian(self) -> bool:
    return True if rp.search("/[WUBRG2]/P\}/i", self._mana_cost["cost"]) else False

