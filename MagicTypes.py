import re


class BaseTypeObject(object):
    types: dict = {}

    @staticmethod
    def _parse_type_line(type_line: str, group: int = 0):
        if 0 > type_line.find("—"):
            return type_line.strip() if 0 == group else ""
        return type_line.split("—")[group].strip()

    def add_types(self, type_list: str) -> None:
        for t in type_list.split(" "):
            self.add_type(t.strip())

    def add_type(self, t: str) -> None:
        if t.strip() in self.types.keys():
            self.types[t.strip()] = True

    def del_types(self, type_list: str) -> None:
        for t in type_list.split(" "):
            self.del_type(t)

    def del_type(self, t: str) -> None:
        if t.strip() in self.types.keys():
            self.types[t.strip()] = False

    def includes(self, type_name: str) -> bool:
        return self.types.get(type_name.strip(), False)

    def excludes(self, type_name: str) -> bool:
        return not self.includes(type_name)

    @property
    def list(self) -> list:
        return [x[0] for x in self.types.items() if x[1]]

    @property
    def string(self) -> str:
        return " ".join(self.list)

    @property
    def count(self) -> int:
        return len(self.list)


class SuperTypes(BaseTypeObject):

    def __init__(self, type_line) -> None:
        self.types = {
            "Basic": False,
            "Elite": False,
            "Host": False,
            "Legendary": False,
            "Ongoing": False,
            "Snow": False,
            "World": False,
        }
        self.add_types(self._parse_type_line(type_line, 0))


class CardTypes(BaseTypeObject):

    def __init__(self, type_line: str) -> None:
        self.types = {
            "Artifact": False,
            "Conspiracy": False,
            "Creature": False,
            "Dungeon": False,
            "Enchantment": False,
            "Instant": False,
            "Land": False,
            "Phenomenon": False,
            "Plane": False,
            "Planeswalker": False,
            "Sorcery": False,
            "Tribal": False,
            "Vanguard": False,
            "Scheme": False,
        }
        self.add_types(self._parse_type_line(type_line, 0))


class SubTypes(BaseTypeObject):
    def __init__(self, type_line: str) -> None:
        self.add_types(self._parse_type_line(type_line, 1))

    def add_type(self, t: str) -> None:
        self.types[t] = True

    def del_type(self, t: str) -> None:
        self.types.pop(t, None)
