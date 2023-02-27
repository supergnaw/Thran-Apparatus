import re

class BaseTypeObject(object):
    @staticmethod
    def _parse_type_line(type_line: str, group: int = 0):
        if 0 > type_line.find("—"):
            return type_line.strip().lower() if 0 == group else ""
        return type_line.split("—")[group].strip().lower()

    def list_types(self):
        return [x.strip("_") for x in dir(self) if re.fullmatch(r"^_[^_]+$", x) and getattr(self, x)]

    def add_types(self, type_list: str) -> None:
        for t in type_list.split(" "):
            self.add_type(t.strip())

    def add_type(self, t: str) -> None:
        if hasattr(self, f"_{t}"):
            setattr(self, f"_{t}", True)

    def del_types(self, type_list: str) -> None:
        for t in type_list.split(" "):
            self.del_type(t.strip())

    def del_type(self, t: str) -> None:
        if hasattr(self, f"_{t}"):
            setattr(self, f"_{t}", False)


    def include(self, type_name: str) -> bool:
        return getattr(self, f"_{type_name.strip().lower()}", False)

    def excludes(self, type_name: str) -> bool:
        return not self.include(type_name)

    @property
    def count(self) -> int:
        return len(self.list_types())


class SuperTypes(BaseTypeObject):

    def __init__(self, type_line):
        self._basic: bool = False
        self._elite: bool = False
        self._host: bool = False
        self._legendary: bool = False
        self._ongoing: bool = False
        self._snow: bool = False
        self._world: bool = False
        self.add_types(self._parse_type_line(type_line, 0))


class CardTypes(BaseTypeObject):

    def __init__(self, type_line: str):
        self._artifact: bool = False
        self._creature: bool = False
        self._enchantment: bool = False
        self._instant: bool = False
        self._land: bool = False
        self._planeswalker: bool = False
        self._sorcery: bool = False
        self._tribal: bool = False
        self._dungeon: bool = False
        self._plane: bool = False
        self._phenomenon: bool = False
        self._vanguard: bool = False
        self._scheme: bool = False
        self._conspiracy: bool = False
        self.add_types(self._parse_type_line(type_line, 0))


class SubTypes(BaseTypeObject):
    def __init__(self, type_line: str):
        self.add_types(self._parse_type_line(type_line, 1))

    def add_type(self, t: str) -> None:
        setattr(self, f"_{t}", True)
