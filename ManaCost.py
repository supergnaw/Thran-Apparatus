import replus as rp

mana_cost: str = ""
_colors: list = []
cmc: float = 0.0
_colorless: bool = False
_monocolored: bool = False
_multicolored: bool = False
_phyrexian: bool = False
_hybrid: bool = False

def __init__(self, mana_cost: str = None):
    self.cost = mana_cost

@property
def cost(self) -> str:
    return self.mana_cost

@cost.setter
def cost(self, mana_cost: str) -> None:
    self._mana_cost = mana_cost

@property
def colors(self) -> list:
    pass

@property
def colors(self) -> float:
    pass

@property
def colorless(self) -> bool:
    pass

@property
def monocolored(self) -> bool:
    pass

@property
def multicolored(self) -> bool:
    pass

@property
def hybrid(self) -> bool:
    return True if rp.search("/\{[WUBRG2]/[WUBRG](\/P)?\}/i", self._mana_cost["cost"]) else False

@property
def phyrexian(self) -> bool:
    return True if rp.search("/[WUBRG2]/P\}/i", self._mana_cost["cost"]) else False

