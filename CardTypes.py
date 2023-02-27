import inspect

artifact = False
creature = False
enchantment = False
instant = False
land = False
planeswalker = False
sorcery = False
tribal = False
dungeon = False
plane = False
phenomenon = False
vanguard = False
scheme = False
conspiracy = False
_count = 0


def __init__():
    pass


def set_types(type_list: list):
    mbrs = inspect.getmembers()
    for t in type_list:
        if t.lower() in mbrs:
            if getattr(t.lower(), False):
                setattr(t.lower(), True)
            else:
                setattr(t.lower(), False)