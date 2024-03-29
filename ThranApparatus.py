# STANDARD IMPORTS
import collections
import datetime
import hashlib
import inspect
import json
import numpy
import os
import requests
import time
import tomllib
import zipfile

# TYPING
from typing import AnyStr, Dict, Any, List

# NON-STANDARD IMPORTS
# import tqdm # for progress bar
import cv2  # opencv-python

import replus
# NOTINVENTEDHERESYNDROME
import replus as rp
from MagicTypes import SuperTypes, CardTypes, SubTypes
from ManaCost import ManaCost

DEFAULT_ART_DIRECTORY = f".{os.path.sep}art{os.path.sep}original"

class ScryfallDataObject(object):
    _mana_cost: ManaCost = None
    _type_line: str = None
    supertypes: SuperTypes = None
    cardtypes: CardTypes = None
    subtypes: SubTypes = None

    # _types = MagicTypes()
    def __init__(self, card_json: str | dict) -> None:
        # Input validation(?)
        if isinstance(card_json, str):
            card_json = json.loads(card_json)

        # Set attributes for object
        """
            This literally isn't necessary, it was just for making coding easier because
            typing card.mana_cost was easier to implement than card['mana_cost'] because
            I'M LAZY
        """
        for key, value in card_json.items():
            setattr(self, key, value)

    @property
    def mana_cost(self):
        return self._mana_cost

    @mana_cost.setter
    def mana_cost(self, mana_cost: str | dict):
        self._mana_cost = ManaCost(mana_cost)

    @property
    def type_line(self) -> str:
        return self._type_line

    @type_line.setter
    def type_line(self, type_line: AnyStr) -> None:
        self._type_line = type_line
        self.supertypes = SuperTypes(str(type_line))
        self.cardtypes = CardTypes(str(type_line))
        self.subtypes = SubTypes(str(type_line))


class ThranApparatus:
    __version__ = "4.3"
    last_update = "2023-01-18"
    _last_api_call = 0
    _template = None
    _config = None
    _card_list = []
    _card_data = []
    _card_image = None

    # Directories
    _dir_art_default = f"./art/default"
    _dir_cache_cards = f"./_cache/scryfall/cards"
    _dir_cache_search = f"./_cache/scryfall/search"
    _dir_cache_mana_cost = f"./_cache/scryfall/mana_cost"
    _dir_cache_err = f"./_cache/scryfall/error"
    _dir_cache_art = f"./_cache/art"
    _dir_cache_text = f"./_cache/text"
    _dir_renders = f"./renders"
    _dir_logs = "./logs"
    _dir_templates = "./templates"

    # Logging
    _log_file_name = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S.log")

    # ---- Initializations ---- #
    def __init__(self, **kwargs: dict) -> None:
        # self._test()
        self._art_directory = kwargs.get("art_directory", self._dir_art_default)
        self._force_overwrite = kwargs.get("force_overwrite", False)
        self._input = kwargs.get("input", None)
        self._reminder = kwargs.get("reminder", False)
        self._template = kwargs.get("template", "classicRedux")
        self._output = kwargs.get("output", self._dir_renders)
        self._verbose = kwargs.get("verbose", 0)
        self._extra_options = kwargs.get("extra_options", [])

        self.show_logo()
        self.make_dirs()

        if self._input:
            print(f"\n========== Loading Template ==========")
            self.load_template(self._template)

        print(f"\n========== Parsing Card List ==========")
        if not self.load_card_list(self._input):
            pass

        print(f"\n========== Fetching Card Data ==========")
        if not self.fetch_card_list(self._card_list):
            pass

        print(f"\n========== Rendering Cards ==========")
        if self._card_list:
            self.render_card_list()

    def _test(self):
        sda = ScryfallDataObject()
        sda.type_line = "Legendary Creature — Bird Serpent"
        print(sda.supertypes)
        print(sda.cardtypes)
        print(sda.subtypes)
        print(sda.types)
        sda.mana_cost = "{3}{W/U}{W/U}"
        print(sda.colorless)
        print(sda.monocolored)
        print(sda.multicolored)
        print(sda.hybrid)
        print(sda.phyrexian)
        self.kill_err("Testing Complete")

    def show_logo(self) -> None:
        versioning = f"Version: {self.__version__}  Updated: {self.last_update}"
        print(f"""
  _____ _                                           
 |_   _| |__  _ __ __ _ _ __                        
   | | | '_ \| '__/ _` | '_ \                       
   | | | | | | | | (_| | | | |                      
   |_| |_| |_|_|  \__,_|_| |_|        _             
    / \   _ __  _ __   __ _ _ __ __ _| |_ _   _ ___ 
   / _ \ | '_ \| '_ \ / _` | '__/ _` | __| | | / __|
  / ___ \| |_) | |_) | (_| | | | (_| | |_| |_| \__ \ 
 /_/   \_\ .__/| .__/ \__,_|_|  \__,_|\__|\__,_|___/
         |_|   |_| {versioning}""")
        return None

    # ---- API Facilitation ---- #
    def _make_rest_call(self, endpoint: AnyStr):
        # Normalize the endpoint URI
        uri = f"https://api.scryfall.com/{endpoint.replace('https://api.scryfall.com/', '')}"

        # Check for existing json in cache
        pattern = f"^.*{self._generate_md5_hash(uri)}\\.json$"
        cached_json = self._check_scryfall_cache(pattern)
        if isinstance(cached_json, str) and not self._force_overwrite:
            json_data = self._load_json(cached_json)
        else:
            # Rate limiter (read more here) --> https://scryfall.com/docs/api
            t_diff = time.time() - self._last_api_call
            if 0.1 > t_diff:
                self._verbose_logging(f"API limit hit ({t_diff}), sleeping for {0.1 - t_diff} seconds", 0, 2)
                time.sleep(0.1 - t_diff)
            self._last_api_call = time.time()

            # URI builder
            try:
                response = requests.get(uri)
                json_data = json.loads(response.text)
            except Exception as err1:
                self._verbose_logging(f"{type(err1)} {err1.args[0].__dict__.get('reason', None)}: {uri}", 0, 1)
                return False

            self._save_response_json(uri, json_data)

            if 200 != response.status_code or "error" == json_data.get("object", False):
                self._verbose_logging(f"Error from \"{uri}\" ({response.status_code}): {response.text}", 0, 1)
                return False

        # There's more data so we have to go deeper
        if self._response_has_more(json_data):
            recursed_data = json_data.get("data", [])
            if json_data.get("has_more", False) and json_data.get("next_page", False):
                self._verbose_logging(f"List has more data: {json_data['next_page']}", 0, 2)
                more_json = self._make_rest_call(json_data["next_page"])[0]
                if isinstance(more_json, dict):
                    recursed_data += more_json
            json_data["data"] = recursed_data

        if not isinstance(json_data, dict):
            self.kill_err(f"Type {type(json_data)} returned from {uri}")

        return json_data

    def _response_has_more(self, response: dict) -> bool:
        if not "list" == response.get("object", False):
            return False
        if not response.get("has_more", False):
            return False
        if not response.get("next_page", False):
            return False
        return True

    def _check_scryfall_cache(self, pattern: AnyStr, search_method: str = "findall") -> str | bool:
        for cache_dir in [member for member, member_type in inspect.getmembers(self) if member.startswith("_dir_cache")]:
            cache = getattr(self, cache_dir)
            for f in os.listdir(cache):
                if getattr(rp, search_method)(pattern, f):
                    print(f"pattern: {pattern}")
                    self._verbose_logging(f"Using cached Scryfall data: {f}", 0, 3)
                    return self._fix_dir_sep(f"{cache}/{f}")
        print(f"No matches found in cache for {pattern}")
        return False

    def _parse_cache_filename(self, uri: str, content: dict):
        hash = self._generate_md5_hash(uri)
        if "card" == content.get("object", False):
            return f"{content['name']}_{content['set']}_{content['collector_number']}_{content['id']}_{hash}.json"
        if "mana_cost" == content.get("object", False):
            return rp.sub('/[^A-Z0-9\\-]+/i', '_', content['cost'].replace("/","-")).strip('_') + f"_{hash}.json"
        if "error" == content.get("object", False):
            return f"{content.get('status', 'unknown')}_{hash}.json"
        if "list" == content.get("object", False):
            return rp.sub("/[^\w]+/", "-", uri).strip("-") + f"_{hash}.json"
        return None

    def _generate_md5_hash(self, s: AnyStr) -> str:
        return hashlib.md5(str(s).encode('utf-8')).hexdigest()

    def fetch_card_list(self, card_list=None) -> list:
        card_list = card_list if card_list else self._card_list
        card_data = []

        for card in card_list:
            print(card)
            c = self.fetch_card(card_name=card['name'], card_set_id=card['set'], card_collector_number=card['num'])
            if c:
                card_data.append(c)

        self._card_data = card_data
        return card_data

    def fetch_card(self, card_name: str = "", card_id: str = "", card_set_id: str = "", card_collector_number: str = "") -> object | None:
        card_json = False

        if card_id:
            card_json = self._make_rest_call(f"cards/{card_id}")
        if card_set_id and card_collector_number:
            card_json = self._make_rest_call(f"cards/{card_set_id}/{card_collector_number}")
        if card_name:
            card_json = self._make_rest_call(f"cards/named?exact={card_name.replace(' ', '+')}")
            if card_set_id and card_json.get("prints_search_uri", False):
                for card in self._make_rest_call(card_json["prints_search_uri"]).get("data", []):
                    card_json = card if card_set_id == card.get("set", False) else card_json
            elif card_json:
                card_json = card_json[0] if isinstance(card_json, tuple) or isinstance(card_json, list) else card_json

        try:
            if not card_json or "card" != card_json.get("object", False):
                return None
            print(f"card_json ({type(card_json)}): {card_json}")
            card_json['mana_cost'] = self.parse_mana_cost(card_json['mana_cost']) if card_json['mana_cost'] else card_json['mana_cost']
            card = ScryfallDataObject(card_json)
            print(card.subtypes, card.cardtypes, card.subtypes, card.mana_cost)
            return card
        except:
            self.kill_err(f"card_json ({type(card_json)}): {card_json}")

    def parse_mana_cost(self, mana_cost: AnyStr) -> dict:
        return self._make_rest_call(f"https://api.scryfall.com/symbology/parse-mana?cost={mana_cost.strip()}")

    def _parse_mana_cost_helper(self, mana_properties: dict) -> dict:
        mana_properties["hybrid"] = True if rp.search("/\{[WUBRG2]/[WUBRG](\/P)?\}/i", mana_properties["cost"]) else False
        mana_properties["phyrexian"] = True if rp.search("/[WUBRG2]/P\}/i", mana_properties["cost"]) else False
        return mana_properties

    def _parse_types(self, card: dict) -> dict:
        types = rp.findall('/(Artifact|Creature|Enchantment|Instant|Land|Planeswalker|Sorcery)/i', card['type_line'])
        if 1 == len(types):
            card['super_type'] = "".join(types)
        else:
            card['super_type'] = "Multiple"
        card['supertypes'] = "".join(types) if 1 == len(types) else "Multiple"

    def _load_json(self, filename: str) -> dict:
        with open(filename, "r") as f:
            content = f.read()
        return json.loads(content)

    def _save_response_json(self, uri: str, content: str | dict):
        cache_grab: dict = {
            'card': self._dir_cache_cards,
            'mana_cost': self._dir_cache_mana_cost,
            'list': self._dir_cache_search,
            'error': self._dir_cache_err,
        }

        if isinstance(content, str):
            content = json.loads(content)

        target_cache = cache_grab.get(content.get("object"), False)
        filename = self._parse_cache_filename(uri, content)

        # Cache logging
        if "card" == content.get("object", False):
            self._verbose_logging(f"Adding new card to cache: {content['name']} ({content['set'].upper()})")
        if "mana_cost" == content.get("object", False):
            self._verbose_logging(f"Adding new mana cost to cache: {content['cost']}")
        if "list" == content.get("object", False):
            self._verbose_logging(f"Adding new search to cache: {uri}", 0, )
        if "error" == content.get("object", False):
            self._verbose_logging(f"Adding new error to cache: {content['status']} ({uri})", 0, 2)

        try:
            with open(self._fix_dir_sep(f"{target_cache}/{filename}"), "w") as outfile:
                outfile.write(json.dumps(content, indent=4))
                return True
        except Exception as e:
            self.kill_err(e)

    # ---- Informational Functions ---- #

    def kill_err(self, err: str | AnyStr, more: AnyStr = None) -> None:
        msg: str | AnyStr = f"{err}: {more}" if not None == more else err
        self._add_log(msg)
        raise SystemExit(f"⛔ {msg}")

    def _verbose_logging(self, msg: str | AnyStr, level: int = 0, icon: int = 0) -> None:
        icons: dict = {
            0: "✅ " # Success
            , 1: "⛔ " # Error
            , 2: "⚠️ " # Warning
            , 3: "ℹ️ " # Info
        }
        if self._verbose < level:
            return None
        print(f"{icons.get(icon, '')}{msg}")
        self._add_log(msg)
        return None

    def _add_log(self, msg: AnyStr) -> None:
        try:
            log_file = self._fix_dir_sep(f"{self._dir_logs}/{self._log_file_name}")
            with open(log_file, mode="a+", encoding="utf-8", newline=str("\n" if str(os.name) == "nt" else "\r\n")) as file_obj:
                file_obj.write(f"[{self._log_timestamp()}] {msg}{os.linesep}")
        except Exception as e:
            self.kill_err(e)
        return None

    def _log_timestamp(self) -> str:
        return str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # ---- Template Functions ---- #
    @staticmethod
    def show_templates() -> None:
        templateDirs = os.listdir(ThranApparatus._dir_templates)
        print(f"\navailable templates ({len(templateDirs)}):")
        for d in templateDirs:
            print(f"  * {d}")
        return None

    def _template_search_caseinsensitive(self, template: AnyStr) -> str | bool:
        template = template.strip() if template.endswith(".zip") else f"{template}.zip".strip()
        for t in os.listdir(ThranApparatus._dir_templates):
            if template.lower() == t.lower():
                return self._fix_dir_sep(f"{self._dir_templates}/{t}")
        return False

    def load_template(self, template: AnyStr = "classicRedux") -> None:
        self._verbose_logging(f"Searching for specified template: \"{template}\"", 0, 3)
        templatePath = self._template_search_caseinsensitive(template)
        if not os.path.exists(templatePath):
            self.kill_err(f"Could not find template: '{templatePath}'")
        self._template_archive = zipfile.ZipFile(templatePath, 'r')
        self._verbose_logging(f"Template loaded: {templatePath}", 0, 3)
        self.read_config()

    def read_config(self) -> None:
        self._verbose_logging("Loading template configuration file...", 0, 3)
        try:
            self._config = tomllib.load(self._template_archive.open('config.toml'))
        except tomllib.TOMLDecodeError as e:
            self.kill_err(f"Config parsing error [TOMLDecodeError]:", f"! {e}")
        except KeyError as e:
            self.kill_err(f"Config loading error [KeyError]:", f"! {e}")
        self._verbose_logging("Template configuration loaded!", 0, 0)

    # ---- Archive I/O & Directory Functions ---- #
    def make_dirs(self) -> None:
        for n, d in self._get_class_dirs().items():
            if not os.path.exists(d):
                self._verbose_logging(f"Making directory path: {d}", 0, 2)
                os.makedirs(d, exist_ok=True)

    def _get_class_dirs(self, dirs = {}) -> dict[str, Any]:
        for member, value in inspect.getmembers(self):
            if member.startswith('_dir'):
                dirs[member] = self._fix_dir_sep(value)
        return dirs

    def _fix_dir_sep(self, dir_path: str) -> str:
        return str(os.path.sep).join(rp.split(r"/[\\/]+/", dir_path))

    # ---- Input/Output Functions ---- #
    def unzip_template(self, template):
        pass

    def load_card_list(self, file_name: AnyStr) -> list[Any]:
        # load file
        if not os.path.exists(file_name):
            self.kill_err(f"Missing card list file: {file_name}")

        self._verbose_logging(f"Reading card list file: {file_name}", 0, 3)
        with open(file_name) as f:
            lines = [line for line in f.readlines() if line.strip()]

        # check for cards
        if 0 >= len(lines):
            self.kill_err("No cards found in card list file")

        self._verbose_logging(f"Found {len(lines)} possible cards in \"{file_name}\"", 0, 3)

        # parse the file
        self._verbose_logging("Parsing list contents for valid cards.", 0, 3)
        cards = []
        regex = rp.compile('/^(\d+x?\s*)?([^(]+)(\(([\w]+)(:(\w+))?)?/i')
        maxNameLen = 0
        maxSetLen = 0
        maxNumLen = 0

        for line in lines:
            # print(line)
            # line = rp.sub(r'(\[[^\]]+\]|\*[^\*]+\*)', '', line).strip()
            # print(line)
            matches = rp.findall(regex, rp.sub(r'(\[[^\]]+\]|\*[^\*]+\*|#.*$)', '', line).strip())
            if not matches:
                self._verbose_logging(f"No card detected: {line.strip()}", 0, 2)
                continue

            m = matches[0]
            card = {}
            card['name'] = m[1].strip()
            maxNameLen = max(len(card['name']), maxNameLen)
            card['set'] = m[3].strip().lower()
            maxSetLen = max(len(card['set']), maxSetLen)
            card['num'] = m[5].strip().lower()
            maxNumLen = max(len(card['num']), maxNumLen)
            cards = cards + [card]

        count = len(cards)
        if 0 >= count:
            self.kill_err("No valid syntax found in cardlist file.")

        cards = [card for n, card in enumerate(cards) if card not in cards[:n]]
        dupes = count - len(cards)
        if 0 < dupes:
            ent = 'entry' if 1 == dupes else 'entries'
            self._verbose_logging(f"Removed {dupes} duplicate {ent} from card list.", 0, 3)

        self._verbose_logging(f"Found {len(cards)} cards in input list", 0, 0)

        if 2 <= self._verbose:
            print("{name:.^{mnl}}.....{set:.^{msl}}.....{num:.^{mul}}".format(
                name="Card Name", set="Set", num="Col.Num",
                mnl=maxNameLen, msl=maxSetLen, mul=maxNumLen))
            for card in cards:
                print("{name:<{mnl}}     {set:<{msl}}     {num:<{mul}}".format(
                    name=card['name'], set=card['set'], num=card['num'],
                    mnl=maxNameLen, msl=maxSetLen, mul=maxNumLen))

        self._card_list = cards
        return cards

    # ---- Normalizing Functions ---- #
    def deprecated_normalize_properties(self, card):
        # Variables
        # self.json = card
        self.type_line = card['type_line']
        self.oracle_text = card['oracle_text']
        self.colors = card['colors']
        # card['dfc'] =

        # Mana Fixing
        card['hybrid'] = True if 0 < len(rp.findall("([^A-Z\d\{\}])", card['mana_cost'])) else False
        card['mana_cost'] = rp.sub("([^A-Z\d\{\}])", '', card['mana_cost'])

        # Legendary Status
        # card['legendary'] =

        # Supertype
        types = rp.findall("(Artifact|Creature|Enchantment|Instant|Land|Planeswalker|Sorcery)", card['type_line'])
        if 1 == len(types):
            card['super_type'] = "".join(types)
        else:
            card['super_type'] = "Multiple"

        # Colors
        if "Land" in card['type_line']:
            card['colors'] = card['produced_mana']
        if 0 == len(card['colors']):
            card['colors'] = ['C']
        card['colors'] = "".join(self.depricated_sort_colors(card['colors']))

        # Frames (from most to least restrictive)
        if "Augment" in card['oracle_text']:
            card['frame'] = "augment"
        elif "Host" in card['type_line']:
            card['frame'] = "host"
        elif "Devoid" in card['oracle_text']:
            card['frame'] = "devoid"
        elif "Token" in card['type_line']:
            card['frame'] = "token"
        elif 1 == card['full_art']:
            card['frame'] = "full"
        elif "Saga" in card['type_line']:
            card['frame'] = "saga"
        elif "Land" in card['type_line']:
            card['frame'] = "artifact"
        elif "Artifact" in card['type_line']:
            card['frame'] = "artifact"
        else:
            card['frame'] = "normal"

        return card

    def deprecated_sort_colors(self, colors):
        # only one color
        if 1 == len(colors):
            return colors

        # Guilds
        if 2 == len(colors):
            combos = [
                ['W', 'U'],  # Azorius
                ['U', 'B'],  # Dimir
                ['B', 'R'],  # Rakdos
                ['R', 'G'],  # Gruul
                ['R', 'W'],  # Boros
                ['G', 'W'],  # Selesnya
                ['W', 'B'],  # Orzhov
                ['B', 'G'],  # Golgari
                ['G', 'U'],  # Simic
                ['U', 'R']  # Izzet
            ]
            for combo in combos:
                if set(combo) == set(colors):
                    return combo

        # Shards/Arcs & Wedges
        if 3 == len(colors):
            combos = [
                ['W', 'U', 'B'],  # Esper
                ['U', 'B', 'R'],  # Grixis
                ['B', 'R', 'G'],  # Jund
                ['R', 'G', 'W'],  # Naya
                ['G', 'W', 'U'],  # Bant
                ['W', 'B', 'G'],  # Abzan
                ['B', 'G', 'U'],  # Sultai
                ['G', 'U', 'R'],  # Temur
                ['U', 'R', 'W'],  # Jeskai
                ['R', 'W', 'B']  # Mardu
            ]
            for combo in combos:
                if set(combo) == set(colors):
                    return combo

        # Guildpacts
        if 4 == len(colors):
            combos = [
                ['W', 'U', 'B', 'R'],  # Yore
                ['U', 'B', 'R', 'G'],  # Glint
                ['B', 'R', 'G', 'W'],  # Dune
                ['R', 'G', 'W', 'U'],  # Ink
                ['G', 'W', 'U', 'B']  # Witch
            ]
            for combo in combos:
                if set(combo) == set(colors):
                    return combo

        # WUBRG
        if 5 == len(colors):
            combo = ['W', 'U', 'B', 'R', 'G']
            if set(combo) == set(colors):
                return combo

        # No matches!!! What the heck are these extra colors???
        colors = ",".join(colors)
        self.kill_err(f"! Invalid color combination: {colors}")

    # ---- Image Processing Functions ---- #
    # Source: https://github.com/6o6o/fft-descreen/blob/master/descreen.py
    # License: MIT License
    def fft_descreen(self, input, output, threshold: int = 92, radius: int = 6, middle: int = 4):
        # check for output extension
        root, ext = os.path.splitext(output)
        if not ext:
            ext = '.png'
        output = root + ext

        #
        img = numpy.float32(cv2.imread(input).transpose(2, 0, 1))
        rows, cols = img.shape[-2:]
        coefs = self.fft_descreen_normalize(rows, cols)
        mid = middle * 2
        rad = radius
        ew, eh = cols // mid, rows // mid
        pw, ph = (cols - ew * 2) // 2, (rows - eh * 2) // 2
        middle = numpy.pad(self.fft_descreen_ellipse(ew, eh),
                           ((ph, rows - ph - eh * 2 - 1),
                            (pw, cols - pw - ew * 2 - 1)),
                           'constant')

        for i in range(3):
            fftimg = cv2.dft(img[i], flags=18)
            fftimg = numpy.fft.fftshift(fftimg)
            spectrum = 20 * numpy.log(cv2.magnitude(fftimg[:, :, 0], fftimg[:, :, 1]) * coefs)

            src = numpy.float32(numpy.maximum(0, spectrum))
            ret, thresh = cv2.threshold(src, threshold, 255, cv2.THRESH_BINARY)
            thresh *= 1 - middle
            thresh = cv2.dilate(thresh, self.fft_descreen_ellipse(rad, rad))
            thresh = cv2.GaussianBlur(thresh, (0, 0), rad / 3., 0, 0, cv2.BORDER_REPLICATE)
            thresh = 1 - thresh / 255

            img_back = fftimg * numpy.repeat(thresh[..., None], 2, axis=2)
            img_back = numpy.fft.ifftshift(img_back)
            img_back = cv2.idft(img_back)
            img[i] = cv2.magnitude(img_back[:, :, 0], img_back[:, :, 1])

        cv2.imwrite(output, img.transpose(1, 2, 0))

    def fft_descreen_normalize(self, h, w):
        x = numpy.arange(w)
        y = numpy.arange(h)
        cx = numpy.abs(x - w // 2) ** 0.5
        cy = numpy.abs(y - h // 2) ** 0.5
        energy = cx[None, :] + cy[:, None]
        return numpy.maximum(energy * energy, 0.01)

    def fft_descreen_ellipse(self, w, h):
        offset = (w + h) / 2. / (w * h)
        y, x = numpy.ogrid[-h: h + 1., -w: w + 1.]
        return numpy.uint8((x / w) ** 2 + (y / h) ** 2 - offset <= 1)

    def enhance_image(self, input, output, color=1.25, sharpness=3):
        if not self.file_exists(input):
            self.kill_err(f"Cannot find image to enhance: {input}")

        img = Image.open(input)
        img = ImageEnhance.Color(img).enhance(color)
        img = ImageEnhance.Sharpness(img).enhance(sharpness)
        img.save(output)

    def download_art(self, cardJSON, forceDownload=False):
        targetDir = os.path.join('art', 'default', '_' + cardJSON['set'])
        filename = cardJSON['image_uris']['art_crop'].split('/')[-1].split('?')[0]
        fullpath = os.path.join(targetDir, filename)
        os.makedirs(targetDir, exist_ok=True)
        if not os.path.exists(fullpath) or forceDownload:
            data = requests.get(cardJSON['image_uris']['art_crop'], allow_redirects=True)
            if data.status_code == 200:
                # print( f"  - Saving {symbol['symbol']}" )
                with open(fullpath, 'wb') as fh:
                    fh.write(data.content)
            else:
                print(f"  - Error: status code {data.status_code} for {uri}")
        else:
            print(f"- Art already downloaded, using existing file")

        return fullpath

    def optimize_art(self, cardJSON, forceOptimize=False, threshold=92, radius=6, middle=4, color=1.25, sharpness=1.25):
        sourceDir = os.path.join('art', 'default', '_' + cardJSON['set'])
        targetDir = os.path.join('art', 'optimized', '_' + cardJSON['set'])
        filename = cardJSON['image_uris']['art_crop'].split('/')[-1].split('?')[0]
        sourceFull = os.path.join(sourceDir, filename)
        targetFull = os.path.join(targetDir, filename)
        os.makedirs(targetDir, exist_ok=True)
        if not os.path.exists(targetFull) or forceOptimize:
            self.fft_descreen(sourceFull, targetFull, threshold, radius, middle)
            self.enhance_image(targetFull, targetFull, color, sharpness)
            if not os.path.exists(targetFull):
                print("! Something went wrong and the optimized art is now missing")
                return False
        else:
            print(f"- Art already optimized, using existing file")
            return True
        return True

    def verify_custom_art(self, art=''):
        if not art:
            return False

        for a in art.split(':'):
            fullpath = os.path.join(DEFAULT_ART_DIRECTORY, a)
            if not os.path.exists(fullpath):
                print(f"! Failed to find custom art: {fullpath}")
                return False
            else:
                print(f"- Custom art verified: {fullpath}")
        return True

    # ---- TEXT FUNCTIONS ---- #
    def wrap_text(self, text, width, height, fontPath, fontSize, lineSpace=0.25, paraSpace=2):
        lines = []
        symbols = []

        words = text.split(" ")
        fontFace = ImageFont.truetype(fontPath, fontSize)
        fontFaceParagraph = ImageFont.truetype(fontPath, int(fontSize / paraSpace))
        line = ""
        totalHeight = 0

        for i, word in enumerate(words):
            if "\n" == word:
                # Newline character, save current line...
                w, h = fontFace.getsize(line)
                lines.append({"line": line, "w": w, "h": h, "size": fontSize, "yOffset": totalHeight})
                line = ""
                totalHeight = totalHeight + h

                # ...and add a paragraph break
                w, h = fontFaceParagraph.getsize(" ")
                lines.append({"line": " ", "w": w, "h": h, "size": int(fontSize / paraSpace)})
                line = ""
                totalHeight = totalHeight + h
            else:
                syms = rp.findall(r'\{[^\}+]\}', word)
                if 0 < len(syms):
                    for sym in syms:
                        # Get location of symbol in word string
                        location = word.find(sym)
                        # print( f"{sym} @ {location}: {word}" )
                        # print( word )

                        # Add padding replacement where symbol should go
                        padding = ""
                        while True:
                            # Add more padding
                            padding = padding + " "
                            w, h = fontFaceParagraph.getsize(padding)
                            # print( f"padding: '{padding}'" )
                            # If padding threashold has been reached
                            if w >= h:
                                # Splice padding into word
                                line = line + word[:location] + padding
                                xOffset, h = fontFaceParagraph.getsize(padding)
                                symbols.append({"symbol": sym, "size": h, "yOffset": totalHeight, "xOffset": xOffset})
                                word = word[location + len(sym):]
                                break
                    wOld, h = fontFace.getsize(f"{line} ")
                    w, h = fontFace.getsize(f"{line} {padding}")

                    if w <= width:
                        line = f"{line} {padding}{word}"
                        lines.append({"line": line, "w": w, "h": h, "size": fontSize})
                        symbols.append({"symbol": sym, "size": h, "yOffset": totalHeight, "xOffset": wOld})
                        totalHeight = totalHeight + h + (lineSpace * fontSize)
                # print( "symbol" )
                else:
                    w, h = fontFace.getsize(f"{line} {word}")
                    # Less than the length, add the word
                    if w <= width:
                        line = f"{line} {word}"

                        # End this line
                        if i == len(words) - 1:
                            w, h = fontFace.getsize(line)
                            lines.append({"line": line, "w": w, "h": h, "size": fontSize})
                            totalHeight = totalHeight + h + (lineSpace * fontSize)
                    # This new word pushes it past the limit
                    else:
                        w, h = fontFace.getsize(line)
                        lines.append({"line": line, "w": w, "h": h, "size": fontSize})
                        line = f"{word}"
                        totalHeight = totalHeight + h + (lineSpace * fontSize)

        # for line in lines:
        #     w, h = fontFace.getsize(f"{line['line']}")

        totalHeight = totalHeight - (lineSpace * fontSize)
        if totalHeight > height:
            # Recursively shrink that font size until you get it right!
            return self.wrap_text(text, width, height, fontPath, fontSize - 1, lineSpacing, paraSpace)
        else:
            print(f"  - Optimum font-size: {fontSize}")
            print(f"  - Textblock height: {totalHeight}")
            print(f"  - Total Symbols: {len(symbols)}")
            return lines, totalHeight, symbols

    def wrap_rules_text(self, oracleText, flavorText, width, height, oFont, fFont, fontSize):
        symbols = []
        lines = []
        x = 0
        y = 0

        # split text into words
        words = oracleText.split(" ")
        oFontFace = ImageFont.truetype(fontPath, fontSize)

        # Prepare loop variables
        l = 0
        x = 0
        y = 0
        w = 0
        line = ""

        # loop through words to get width
        for i, word in enumerate(words):
            if "\n" == word:
                w, h = oFontFace.getsize("Ag")
                # Newline character, save current line...
                y = int(l * (h + (h / 6)))

                lines.append({"line": line, "x": x, "y": y, "w": w, "h": h, "size": fontSize, "type": "oracle"})

                # ...and add a paragraph break...
                l = l + 1
                w, h = oFontFace.getsize("Ag")
                y = int(l * (h + (h / 6)))
                lines.append({"line": " ", "x": 0, "y": y, "w": w, "h": h, "size": fontSize, "type": "oracle"})

                # ...then start a new line
                l = l + 1
                x = 0
                line = ""
            else:
                # Check for symbols in word
                syms = rp.findall(r'\{[^\}+]\}', word)
                if 0 < len(syms) and False:
                    # Symbols exist
                    for sym in syms:
                        # Get location of symbol in word string
                        location = word.find(sym)

                        if 0 < len(line):
                            # If current line already has text
                            line = line + " "
                            if 0 < location:
                                # Combine with current line with any preceeding text
                                line = line + word[:location]

                            # Get line dimensions
                            w, h = oFontFace.getsize(line)
                            # Calculate y offset
                            y = int(l * (h + (h / 6)))
                            # Add line
                            lines.append({"line": line, "x": x, "y": y, "size": fontSize, "type": "oracle"})
                            # Reset values
                            line = ""
                            x = w
                            w = 0
                        else:
                            # No text on line, so get default values for font size
                            w, h = oFontFace.getsize("Ag")  # Using "A" and "g" give largest height
                            w = 0

                        # Add symbol to render list
                        symbols.append({"sym": sym, "x": w + x, "y": y, "size": h})

                        # Remove symbol from word string
                        word = word[location + len(sym):]

                        # Modify row x offset by width of symbol (same as height)
                        x = x + h

                    # Append remaining text
                    w, h = oFontFace.getsize(line)
                    x = x + w
                    y = int(l * (h + (h / 6)))
                    line = word
                    lines.append({"line": word, "x": x + w, "y": y, "w": w, "h": h, "size": fontSize, "type": "oracle"})
                else:
                    # Symbols don't exist
                    w, h = oFontFace.getsize(f"{line} {word}")
                    if (w + x) <= width:
                        # Less than width, add word to line
                        if 0 == len(line):
                            if 0 == x:
                                # Beginning of a new line
                                line = word
                            else:
                                # Line has no next but x offset, probably trailing symbol(s)
                                line = " " + word
                        else:
                            line = f"{line} {word}"
                    else:
                        # Wrap new word
                        w, h = oFontFace.getsize("Ag")
                        y = int(l * (h + (h / 6)))
                        lines.append({"line": line, "x": x, "y": y, "size": fontSize})
                        line = f"{word}"
                        l = l + 1
                        x = 0

            # This is the last word
            if i == len(words) - 1:
                w, h = oFontFace.getsize(line)
                y = int(l * (h + (h / 6)))
                lines.append({"line": line, "x": x, "y": y, "w": w, "h": h, "size": fontSize})

            # Calculate total height
            w, h = oFontFace.getsize(line)
            totalHeight = ((l + 1) * (h + (h / 6))) - (h / 6)
            if totalHeight > height:
                # Recursively reduce text size until it fits
                return self.wrap_rules_text(oracleText, flavorText, width, height, oFont, fFont, fontSize - 1)

        return lines, symbols

    def single_line_kerning(self, text, maxWidth, fontFace, pixelOffset=0):
        # https://stackoverflow.com/questions/58591305/how-to-set-fonts-kerning-in-python-pillow
        img = Image.new("RGBA", (maxWidth, 2000))
        draw = ImageDraw.Draw(img)
        totalWidth = 0
        for i, letter in enumerate(text):
            letterWidth, h = fontFace.getsize(letter)
            totalWidth = totalWidth + letterWidth - pixelOffset
            position = (totalWidth - letterWidth, 20)
            draw.text(position, letter, (255, 255, 255), fontFace)
        if totalWidth > maxWidth:
            img = None
            draw = None
            print(f"! Type line width of {maxWidth}px exceeded ({totalWidth}): kerning -{pixelOffset}px")
            return self.single_line_kerning(text, maxWidth, fontFace, pixelOffset + 1)
        return pixelOffset

    # ---- Rendering Functions ---- #
    def render_card(self, card: object) -> bool:
        print(inspect.getmembers(card))
        print(f"card.mana_cost: {card.mana_cost}")
        print(f"card.cmc: {card.cmc}")
        print(f"card.mana_cost.colorless: {card.mana_cost.colorless}")
        print(f"card.mana_cost.monocolored: {card.mana_cost.monocolored}")
        print(f"card.mana_cost.multicolored: {card.mana_cost.multicolored}")
        print(f"card.mana_cost.hybrid: {card.mana_cost.hybrid}")
        print(f"card.mana_cost.phyrexian: {card.mana_cost.phyrexian}")
        self.kill_err("temporary lock")
        render_dir = self._output if self._output else self._dir_renders
        output = self._fix_dir_sep(f"{render_dir}/{card.name}.png")
        print(self.parse_mana_cost(card.mana_cost))

        return True

        canvas = None

        # Create render directory
        if not self.dir_exists(renderDir):
            os.makedirs(renderDir)

        # Loop through and call all render_layer methods
        for method in dir(self):
            if "render_layer" == method[0:12]:
                layer = getattr(self, method)(card)
                if canvas is None and layer is not None:
                    canvas = layer
                elif canvas is not None and layer is not None:
                    canvas.alpha_composite(layer, (0, 0))
                else:
                    print("- Skipping layer...")

        if canvas is not None:
            # Render text
            canvas = template.render_text(card, canvas)

            print("+ Saving card canvas\n")
            canvas.save(output, format="png")
        else:
            print("! Card failed to render\n")

    def render_card_list(self, card_data=None):
        card_data = self._card_data if not card_data else card_data
        for card in card_data:
            self.render_card(card)


# load cardlist
# print(f"\n===== Loading card list =====\n")
# cardListFile = args.list[0]
# renderDir = os.path.join("renders",os.path.splitext(cardListFile)[0])
# cardList = TA.load_card_list(cardListFile)

# search for card data
if True == False:
    print(f"\n===== Processing Cards =====\n")
    for card in cardList:
        cardJSON = SF.card_search(card['name'], card['set'])
        # no card found
        if None == cardJSON: continue

        # check for no card matches:
        if isinstance(cardJSON, str):
            print(cardJSON)
            continue

        # check if custom art exists
        if card['art']:
            card['custom_arts'] = card['art'] if template.verify_custom_art(card['art']) else ''

        # print("[[[[ Asmoranomardicadaistinaculdacar ]]]]")
        print("=========================================")
        # print(f"[[[[ {card['name']} ]]]]") #31
        print(f"[[[[ {card['name']:^31} ]]]]")  # 31
        print("-----------------------------------------")
        print("* Detecting art status")

        # download scryfall art
        if not card['art']:
            print(f"* Downloading art from set {cardJSON['set'].upper()}")
            template.download_art(cardJSON, args.force)
            print(f"* Optimizing art")
            template.optimize_art(cardJSON, args.force, args.optimize[0], args.optimize[1], args.optimize[2],
                                  args.optimize[3], args.optimize[4])

        print("-----------------------------------------")
        print(f"* Normalizing Card Data...")
        card = template.normalize_properties(cardJSON)
        print(f"- Card properties:")
        print(f"  Colors: {card['colors'].upper()}")
        print(f"  Layout: {card['frame'].capitalize()}")
        print(f"  Type: {card['type_line']}")

        print("-----------------------------------------")
        print("* Rendering Card")
        # template.render_card(card, renderDir)
    # exit()
    print(f"\n===== Normalizing Card Data =====\n")
    for card in cards:
        print(f"- Normalizing {card['name']}...")
        card = template.normalize_properties(card)

    # Loop through cards
    print(f"\n===== Rendering Cards =====\n")
    for card in cards:
        print("---------------------------")
        print(f"[{card['name']}]")
        print(f"* Card properties:")
        print(f"- Colors: {card['colors'].upper()}")
        print(f"- Layout: {card['frame'].capitalize()}")
        print(f"- Type: {card['type_line']}")
        template.render_card(card, renderDir)
    exit()
    print(f" --Loading card data...")
    for item in renderList:
        # print( f"\n  [[ {item} ]]" )
        # # See if card is in database
        # search = {}
        # search["name"] = item
        # if "set" in renderList[item]:
        # 	search["set"] = renderList[item]["set"].lower()
        # if "collector_number" in renderList[item]:
        # 	search["collector_number"] = int( renderList[item]["collector_number"] )
        # rows = search_cards( search )
        #
        # # No cards found
        # if 0 == len( rows ):
        # 	print( f"  - No results, check spelling and try again." )
        # 	continue
        #
        # card = rows_2_cards( rows )
        # card = card[0]
        #
        # if 1 < len( rows ):
        # 	# More than one card found
        # 	prints = []
        # 	for row in rows:
        # 		prints.append( f"{row['set'].upper():<5}:{row['collector_number']:>6}" )
        #
        # 	prints = " | ".join( prints )
        #
        # 	print( f"  - {len( rows )} results, available printings:" )
        # 	headers = "Code :      "
        # 	headers = "Code : Numbr | " * min( len( prints ), 5 ) + "\n    " + "------------ | " * min( len( prints ), 5 )
        # 	print( f"\n    {headers}" )
        # 	prints = word_wrap( prints, 85, " | ", 4 )
        # 	print( f"    {prints}\n" )
        # 	print( f"    * Limit results using set codes and collector numbers." )
        # 	continue
        # 	# print( f"    Using set: {rows[0]['set'].upper()}" )
        # else:
        # 	# Just the right number of 1 found
        # 	print( f"  - {len( rows )} result: {card['name']} ({card['set'].upper()})" )

        # Load style data
        if "style" in renderList[card['name']]:
            if os.path.exists(os.path.join("styles", renderList[card['name']]['style'],
                                           f"{renderList[card['name']]['style']}.json")):
                style = renderList[card['name']]['style']
            else:
                style = "classic"
        else:
            style = "classic"

        styleJSON = load_json(os.path.join("styles", style, "style.json"))

        # Normalize render settings
        if "border" in renderList[card['name']]:
            if renderList[item]["border"].lower() in ["black", "white", "silver", "gold"]:
                border = renderList[item]["border"].lower()
            else:
                border = "black"
        else:
            border = "black"

        # Prep card info for hash
        infoString = f"{card['name']}:{card['set']}:{border}:{style}"

        # Check if card has already been rendered
        # Continue

        # Determine art
        if "custom_art" in item:
            # Custom art
            if None != item["custom_art"]:
                artPath = os.path.join("art", "custom")
                artFile = item["custom_art"]
                useCustomArt = True
            else:
                useCustomArt = False
        else:
            # Default card art
            # uri = card["image_uris"]["png"]
            uri = card["image_uris"]["art_crop"]
            useCustomArt = False

            try:
                artFile = rp.search('\/([\d\w\-]+\.(png|jpg))\??[\d\s]*', uri).group(1)
                artPath = os.path.join("art", "default", f"_{card['set']}")
            except AttributeError:
                print(f"  - Error: failed to parse art uri: {uri}")
                continue

        # Manage art file
        artFullPath = os.path.join(artPath, artFile)
        forceDownload = False
        if not os.path.exists(artFullPath) or forceDownload:
            # Custom art file doesn't exist
            if useCustomArt == True:
                print(f"  - Error: failed find custom art: {artPath}")
                print("      * Skipping render")
                continue

            # Check for directory
            if not os.path.exists(artPath):
                os.makedirs(artPath)

            # Download new art
            data = requests.get(uri, allow_redirects=True)
            if data.status_code == 200:
                print(f"  - Saving cropped art from Scryfall...")
                with open(artFullPath, 'wb') as fh:
                    fh.write(data.content)
                print(f"  - Save complete.")
            else:
                print(f"  - Error: status code {data.status_code} for {uri}")
                continue

            # Check for success
            if not os.path.exists(artFullPath):
                print(f"  - Error: failed to download art: {card['image_uris']['png']}")
                continue

        cacheDir = os.path.join("renders", "_cache")
        renderDir = os.path.join("renders", style)

        if not os.path.exists(os.path.join("renders", "_cache")):
            os.makedirs(cacheDir)
        if not os.path.exists(os.path.join("renders", style)):
            os.makedirs(renderDir)

        # Default image processing
        if False == useCustomArt:
            scale = 4
            threshold = 92  # 92
            radius = int(7 * scale / 2)  # 6
            middle = int(4 * scale / 2)  # 4
            cachePath = os.path.join(cacheDir, f"{card['id']}.png")

            # Scale image and save to cache
            # if os.path.exists( artFullPath ) and not os.path.exists( cachePath ):
            # 	img = Image.open( artFullPath )
            # 	size = img.size
            # 	newSize = ( scale * x for x in img.size )
            # 	img = img.resize( newSize )
            # 	img.save( cachePath )

            # Process image if not exist
            forceRender = False
            if not os.path.exists(cachePath) or forceRender:
                # Scale image
                print(f"  - Scaling image...")
                if os.path.exists(artFullPath) and not os.path.exists(cachePath):
                    img = Image.open(artFullPath)
                    size = img.size
                    newSize = (scale * x for x in img.size)
                    img = img.resize(newSize)
                    img.save(cachePath)

                # Remove rosette pattern
                print(f"  - Processing art to remove rosette pattern...")
                fft_descreen(cachePath, cachePath, threshold, radius, middle)
                if not os.path.exists(cachePath):
                    print(f"  - Error: post-processed cropped art cropped but missing:")
                    print(f"    {cachePath}")
                    continue

                # Enhance colors
                print(f"  - Enhancing image for 3rd-party printing...")
                enhance_image(cachePath, cachePath)

                print(f"  - Processing art complete.")
            else:
                print(f"  - Pre-processed art detected, using existing art.")

        # Normalize card properties for image rendering
        # Colors
        if "land" in card['type_line'].lower():
            card['colors'] = card['produced_mana']
        if "artifact" in card['type_line'].lower() and "land" not in card['type_line'].lower():
            # colors = "-".join( ['a'] + card['colors'] ).lower()
            colors = 'a'
        elif 0 == len(card['colors']):
            colors = 'c'
        elif 2 < len(card['colors']):
            colors = 'm'
        else:
            colors = "-".join(card['colors']).lower()

        # Types
        if "token" in card['type_line'].lower():
            frame = 'token'
        elif "land" in card['type_line'].lower():
            frame = 'land'
        elif "saga" == card['layout'].lower():
            frame = 'saga'
        elif 1 == card['full_art']:
            frame = 'full'
        else:
            frame = 'normal'

        print(f"  - Card properties:")
        print(f"    * Colors: {colors.upper()}")
        print(f"    * Layout: {frame.capitalize()}")
        print(f"    * Type: {card['type_line']}")
        print(f"    * Border: {border}")

        # Prepare text

        # Parepare image layers
        layers = {}
        for i in range(len(styleJSON['layers'])):
            i = str(i)
            if styleJSON['layer_order'][i] in styleJSON['layers'] and True == styleJSON['layers'][
                styleJSON['layer_order'][i]]:
                if 'art' == styleJSON['layer_order'][i]:
                    layers['art'] = Image.open(cachePath)
                elif 'border' == styleJSON['layer_order'][i]:
                    layers['border'] = Image.open(os.path.join("styles", style, "layers", "borders", f"{border}.png"))
                elif 'frame' == styleJSON['layer_order'][i]:
                    layers['frame'] = Image.open(
                        os.path.join("styles", style, "layers", "frames", frame, f"{colors}.png"))
                elif 'frame_effects' == styleJSON['layer_order'][i]:
                    layers['frame_effects'] = Image.open(
                        os.path.join("styles", style, "frame_effects", effects, f"{colors}.png"))
                elif 'background' == styleJSON['layer_order'][i]:
                    layers['background'] = Image.open(os.path.join("styles", style, "backgrounds", f"{colors}.png"))

        # Adjust art size and ratio
        w, h = layers['art'].size
        wDelta = styleJSON['styles'][frame]['art']['width'] / w
        hDelta = styleJSON['styles'][frame]['art']['height'] / h

        # Resize image
        if wDelta > hDelta:
            wNew = int(w * wDelta)
            hNew = int(h * wDelta)
        else:
            wNew = int(w * hDelta)
            hNew = int(h * hDelta)

        layers['art'] = layers['art'].resize((wNew, hNew))

        # Crop image
        w, h = layers['art'].size
        if w > styleJSON['styles'][frame]['art']['width']:
            sideMargin = w - styleJSON['styles'][frame]['art']['width']
            if 'left' == styleJSON['styles'][frame]['art']['hAlign']:
                left = 0
                right = w - sideMargin
            elif 'right' == styleJSON['styles'][frame]['art']['hAlign']:
                left = sideMargin
                right = w
            else:  # take center or middle
                left = sideMargin / 2
                right = w - sideMargin / 2
        else:
            left = 0
            right = w

        if h > styleJSON['styles'][frame]['art']['height']:
            endMargin = h - styleJSON['styles'][frame]['art']['height']
            if 'top' == styleJSON['styles'][frame]['art']['vAlign']:
                top = 0
                bottom = h - endMargin
            elif 'bottom' == styleJSON['styles'][frame]['art']['vAlign']:
                top = endMargin
                bottom = h
            else:  # take center or middle
                top = endMargin / 2
                bottom = h - endMargin / 2
        else:
            top = 0
            bottom = h

        layers['art'] = layers['art'].crop((left, top, right, bottom))

        outputFile = rp.sub(r'[^\w\s\.-]', '', f"{card['name']} ({card['set'].upper()}).png")
        renderPath = os.path.join(renderDir, outputFile)
        canvas = Image.new(mode="RGB", size=layers['border'].size)

        print(f"  - Combining base layers...")
        for i in range(len(styleJSON['layer_order'])):
            i = str(i)
            if styleJSON['layer_order'][i] in styleJSON['layers'] and True == styleJSON['layers'][
                styleJSON['layer_order'][i]]:
                if 'art' == styleJSON['layer_order'][i]:
                    canvas.paste(layers['art'],
                                 (styleJSON['styles'][frame]['art']['x'], styleJSON['styles'][frame]['art']['y']))
                else:
                    canvas.paste(layers[styleJSON['layer_order'][i]], (0, 0), layers[styleJSON['layer_order'][i]])

        # Mana cost
        if 0 < len(card['mana_cost']):
            mana = card['mana_cost'][1:-1].split("}{")
            if True == styleJSON['styles'][frame]['mana']['reverse']:
                mana.reverse()

            print(f"  - Adding {len(mana)} symbols...")
            x = styleJSON['styles'][frame]['mana']['xRoot']
            y = styleJSON['styles'][frame]['mana']['yRoot']
            for i, sym in enumerate(mana, 1):
                xPos = x + ((i - 1) * styleJSON['styles'][frame]['mana']['xChange']) + \
                       styleJSON['styles'][frame]['mana'][str(i)]['x']
                yPos = y + ((i - 1) * styleJSON['styles'][frame]['mana']['yChange']) + \
                       styleJSON['styles'][frame]['mana'][str(i)]['y']
                size = styleJSON['styles'][frame]['mana']['size']
                symbolPath = os.path.join("styles", style, "symbols", f"{sym}.png")
                symbol = Image.open(symbolPath)
                symbol = symbol.resize((size, size))
                # symbolFile = f"{rp.sub( r'[^A-Z0-9]','', mana )}.png"
                canvas.paste(symbol, (xPos, yPos), symbol)

        # Prepare image for drawing text
        drawing = ImageDraw.Draw(canvas)

        # Card name
        fontPath = os.path.join("styles", style, "fonts", styleJSON['styles'][frame]['name']['font'])
        fontSize = int(styleJSON['styles'][frame]['name']['size'])
        fontFace = ImageFont.truetype(fontPath, fontSize)

        # Alignment
        w, h = fontFace.getsize(card['name'])
        x = styleJSON['styles'][frame]['name']['x']
        if 'left' == styleJSON['styles'][frame]['name']['hAlign']:
            x = x
        elif 'right' == styleJSON['styles'][frame]['name']['hAlign']:
            x = x - w + styleJSON['styles'][frame]['name']['width']
        else:
            x = styleJSON['styles'][frame]['name']['x'] + (styleJSON['styles'][frame]['name']['width'] / 2) - (w / 2)

        y = int(styleJSON['styles'][frame]['name']['y'])
        color = tuple(map(int, styleJSON['styles'][frame]['name']['color'].split(",")))

        if rp.match("^\d+,\d+,\d+$", styleJSON['styles'][frame]['name']['shadow']):
            shadowColor = tuple(map(int, styleJSON['styles'][frame]['name']['shadow'].split(",")))
            sx = x + int(styleJSON['styles'][frame]['name']['shadow_offset'])
            sy = y + int(styleJSON['styles'][frame]['name']['shadow_offset'])
            drawing.text((sx, sy), card['name'], shadowColor, font=fontFace)  # shadow

        drawing.text((x, y), card['name'], color, font=fontFace)  # text

        # Type line
        fontPath = os.path.join("styles", style, "fonts", styleJSON['styles'][frame]['type']['font'])
        fontSize = int(styleJSON['styles'][frame]['type']['size'])
        fontFace = ImageFont.truetype(fontPath, fontSize)

        # Alignment
        w, h = fontFace.getsize(card['type_line'])
        x = styleJSON['styles'][frame]['type']['x']
        if 'left' == styleJSON['styles'][frame]['type']['hAlign']:
            x = x
        elif 'right' == styleJSON['styles'][frame]['type']['hAlign']:
            x = x - w + styleJSON['styles'][frame]['type']['width']
        else:
            x = styleJSON['styles'][frame]['type']['x'] + (styleJSON['styles'][frame]['type']['width'] / 2) - (w / 2)

        y = int(styleJSON['styles'][frame]['type']['y'])
        color = tuple(map(int, styleJSON['styles'][frame]['type']['color'].split(",")))

        if rp.match("^\d+,\d+,\d+$", styleJSON['styles'][frame]['type']['shadow']):
            shadowColor = tuple(map(int, styleJSON['styles'][frame]['type']['shadow'].split(",")))
            sx = x + int(styleJSON['styles'][frame]['type']['shadow_offset'])
            sy = y + int(styleJSON['styles'][frame]['type']['shadow_offset'])
            drawing.text((sx, sy), card['type_line'], shadowColor, font=fontFace)  # shadow

        drawing.text((x, y), card['type_line'], color, font=fontFace)  # text

        # Oracle text
        lineSpacing = styleJSON['styles'][frame]['oracle']['line_spacing']

        fontPath = os.path.join("styles", style, "fonts", styleJSON['styles'][frame]['oracle']['font'])
        oFontPath = os.path.join("styles", style, "fonts", styleJSON['styles'][frame]['oracle']['font'])
        # rFontPath = os.path.join( "styles", style, "fonts", styleJSON['styles'][frame]['reminder']['font'] )
        fFontPath = os.path.join("styles", style, "fonts", styleJSON['styles'][frame]['flavor']['font'])
        fontSize = int(styleJSON['styles'][frame]['oracle']['size'])
        color = tuple(map(int, styleJSON['styles'][frame]['oracle']['color'].split(",")))

        w = styleJSON['styles'][frame]['oracle']['width']
        h = styleJSON['styles'][frame]['oracle']['height']

        print(f"  - Processing oracle text to find optimum font size...")
        oracleText = card['oracle_text'].replace("\n", " \n ")
        # oracleText, totalHeight, symbols = wrap_text( oracleText, w, h, fontPath, fontSize, lineSpacing )

        oracleText, symbols = wrap_rules_text(oracleText, "", w, h, fontPath, fontPath, fontSize)
        # 									( oracleText, flavorText, width, height, oFont, fFont, size ):
        # print( oracleText )
        # print( symbols )

        # Add symbols
        if 0 < len(symbols):
            print("  - Adding symbols to image:")
            print("    =======================================")
            print("     xPos | yPos | Width | Height | Symbol")
            print("    ------+------+-------+--------+--------")
            for sym in symbols:
                xPos = sym['x'] + styleJSON['styles'][frame]['oracle']['x']
                yPos = sym['y'] + styleJSON['styles'][frame]['oracle']['y']
                h = sym['size']
                w = sym['size']
                symbolFile = rp.sub(r'(\{|\})', '', sym['sym']) + ".png"
                symbolPath = os.path.join("styles", style, "symbols", symbolFile)
                symbol = Image.open(symbolPath)
                symbol = symbol.resize((w, h))
                print(f"     {xPos:>4} | {yPos:>4} | {w:>5} | {h:>6} | {symbolFile:^6}")
                canvas.paste(symbol, (xPos, yPos), symbol)
            print("    ---------------------------------------")
        else:
            print("  - No symbols in oracle text.")

        # Add oracle text
        maxChars = 0
        for line in oracleText:
            maxChars = max(len(line['line']), maxChars)

        x1 = styleJSON['styles'][frame]['oracle']['x']
        y1 = styleJSON['styles'][frame]['oracle']['y']
        x2 = x + styleJSON['styles'][frame]['oracle']['width']
        y2 = y + styleJSON['styles'][frame]['oracle']['height']
        print(f"  - Adding text to image ({x1},{y1}:{x2},{y2}):")
        print("    =======================" + ("=" * maxChars))
        print("     xPos | yPos | Size | Text")
        print("    ------+------+------+--" + ("-" * maxChars))
        for text in oracleText:
            # print( text )
            fontFace = ImageFont.truetype(oFontPath, text['size'])
            xOffset = text['x'] + styleJSON['styles'][frame]['oracle']['x']
            yOffset = text['y'] + styleJSON['styles'][frame]['oracle']['y']
            drawing.text((xOffset, yOffset), text['line'], color, font=fontFace)

            # for i, line in enumerate( oracleText ):
            # 	if 'left' == styleJSON['styles'][frame]['oracle']['hAlign']:
            # 		xOffset = int( x )
            # 	elif 'right' == styleJSON['styles'][frame]['oracle']['hAlign']:
            # 		xOffset = int( x + w - line['w'] )
            # 	else:
            # 		xOffset = int( x + w / 2 - line['w'] / 2 )
            # 	fontFace = ImageFont.truetype( fontPath, line['size'] )

            print(f"    {xOffset:>6}|{yOffset:>6}|{text['size']:>6}| {text['line']}")
        print("    ----------------------------------------" + ("-" * maxChars))
        # exit()
        # exit()
        # exit()
        # exit()
        # exit()
        # exit()

        # # if 0 < len( symbols ):
        # # 	for sym in symbols:
        # # 		print( sym )
        # # 		fileName = rp.sub( '(\{|\}|\/)', '', sym['symbol'] ).upper() + ".png"
        # # 		filePath = os.path.join( "styles", style, "symbols", fileName )
        # # 		img = Image.open( filePath )
        # # 		img = img.resize(( sym['size'], sym['size'] ))
        # # 		x = int( styleJSON['styles'][frame]['oracle']['x'] + sym['xOffset'] )
        # # 		x = int( styleJSON['styles'][frame]['oracle']['y'] + sym['yOffset'] )
        # # # 		canvas.paste( img, ( x, y ), img )
        # # #
        # maxChars = 0
        # for line in oracleText:
        # 	maxChars = max( len( line['line'] ), maxChars )
        # # #
        # # # x = int( styleJSON['styles'][frame]['oracle']['x'] )
        # # # # if 'left' == styleJSON['styles'][frame]['oracle']['hAlign']:
        # # # # 	x = x
        # # # # elif 'right' == styleJSON['styles'][frame]['oracle']['hAlign']:
        # # # # 	x = x + w
        # # # # else:
        # # # # 	x = x + w / 2
        # #
        # # y = int( styleJSON['styles'][frame]['oracle']['y'] )
        # # if 'top' == styleJSON['styles'][frame]['oracle']['vAlign']:
        # # 	y = y
        # # elif 'bottom' == styleJSON['styles'][frame]['oracle']['vAlign']:
        # # 	y = y + h - totalHeight
        # # else:
        # # 	y = y + ( h / 2 ) - ( totalHeight / 2 )
        #
        # yOffset = int( y )
        # print( "  - Adding text to image:" )
        # print( "    ========================================" + ( "=" * maxChars ))
        # print( "     xPos | yPos | Size | Width | Height | Text" )
        # print( "    ------+------+------+-------+--------+--" + ( "-" * maxChars ))
        # for i, line in enumerate( oracleText ):
        # 	if 'left' == styleJSON['styles'][frame]['oracle']['hAlign']:
        # 		xOffset = int( x )
        # 	elif 'right' == styleJSON['styles'][frame]['oracle']['hAlign']:
        # 		xOffset = int( x + w - line['w'] )
        # 	else:
        # 		xOffset = int( x + w / 2 - line['w'] / 2 )
        # 	fontFace = ImageFont.truetype( fontPath, line['size'] )
        # 	print( f"    {xOffset:^6}|{yOffset:^6}|{line['size']:^6}|{line['w']:^7}|{line['h']:^8}| {line['line']}" )
        # 	# print( f"w-{line['w']:>6}|h-{line['h']:>6} ({xOffset},{yOffset}) @ {line['size']}: {line['line']}" )
        # 	drawing.text(( xOffset, yOffset ), line['line'], color, font=fontFace )
        # 	yOffset = int( yOffset + line['h'] + lineSpacing * line['size'] )
        # print( "    ----------------------------------------" + ( "-" * maxChars ))
        #
        # # render_wrapped_text( lines )
        #
        # if False != styleJSON['styles'][frame]['oracle']['shadow'] and rp.match( "^\d+,\d+,\d+$", styleJSON['styles'][frame]['oracle']['shadow'] ):
        # 	shadowColor = tuple( map( int, styleJSON['styles'][frame]['oracle']['shadow'].split( "," )))
        # 	sx = x + int( styleJSON['styles'][frame]['oracle']['shadow_offset'] )
        # 	sy = y + int( styleJSON['styles'][frame]['oracle']['shadow_offset'] )
        # 	drawing.text(( sx, sy ), card['oracle_text'], shadowColor, font=fontFace ) # shadow

        # drawing.text(( x, y ), card['oracle_text'], color, font=fontFace ) # text

        # Artist

        # Copyright

        # Save to output image
        try:
            print(f"  - Rendering to {renderPath}...")
            canvas.save(renderPath)
            print("  - RENDER COMPLETE!")
        except OSError as e:
            print(f"  - {e}")
