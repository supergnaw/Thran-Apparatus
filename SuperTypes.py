import inspect

basic = False
elite = False
host = False
legendary = False
ongoing = False
snow = False
world = False


def __init__():
    pass


def set_types(type_list: list):
    mbrs = inspect.getmembers()
    for t in type_list:
        if t.lower() in mbrs:
            if getattr(SuperTypes, t.lower(), False):
                setattr(t.lower(), True)
            else:
                setattr(t.lower(), False)