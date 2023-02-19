from typing import AnyStr, Tuple, Dict, Any
import requests
import json
import os
import hashlib


class UpdateFromGit:
    updates = {}

    def __init__(self, uri: AnyStr, script_path: AnyStr = "") -> object:
        self.uri = uri
        self.script_path = script_path if 0 < len(script_path.strip()) else self._resolve_directory()
        self.allowed_updates = ['replus.py']

    def _resolve_directory(self):
        import __main__
        self.script_path = os.path.dirname(os.path.abspath(__main__.__file__))

    def check(self, uri: AnyStr = "") -> tuple[bool, dict[Any, Any]]:
        response = requests.get(uri if 0 < len(uri.strip()) else self.uri)

        if 200 != response.status_code:
            print(f"Invalid target uri for repository: status code {response.status_code} received.")
            return False, {}

        for f in json.loads(response.text):
            # file_name, download_url, remote_hash = f["path"], f["download_url"], f["sha"]
            #
            # print(f"file_name, download_url, remote_hash:\n{file_name}\n{download_url}\n{remote_hash}")
            realpath = os.path.join(self.script_path, f["path"])
            print(realpath)
            if not os.path.exists(realpath):
                # self.updates[f["path"]] = f["download_url"]
                self.updates[realpath] = f
            elif f["sha"] != self.gen_hash(realpath) and f["path"] in self.allowed_updates:
                # self.updates[f["path"]] = f["download_url"]
                self.updates[realpath] = f

        print(json.dumps(self.updates, indent=4))

        return True, self.updates

    def show(self) -> None:
        for key, val in self.updates.items():
            print(f"{key}: {val}")
        return None

    def update(self, target_file: AnyStr, raw_link: AnyStr) -> bool:
        if os.path.exists(target_file) and target_file in self.allowed_updates:
            return self.save_file(raw_link, target_file)

        if not os.path.exists(target_file):
            return self.save_file(raw_link, target_file)

        return False

    def save_file(self, url, filepath) -> bool:
        return True
        response = requests.get(url)
        if 200 != response.status_code:
            print(f"Update failed: status code {response.status_code} received.")
            return False

        with open(filepath, "wb") as f:
            f.write(response.content)

        return os.path.exists(filepath)

    def gen_hash(self, filename: AnyStr) -> str:
        """"This function returns the SHA-1 hash
        of the file passed into it"""
        # read only 1024 bytes at a time
        byte_limit = 1024
        ghash = hashlib.sha1()

        # GitHub prepends files with "blob <file-size>" followed by null character before raw contents
        ghash.update(f"blob {os.stat(filename).st_size}\0".encode("utf-8"))

        # open file for reading in binary mode
        with open(filename, 'rb') as file:
            chunk = 0
            while chunk != b'':
                chunk = file.read(byte_limit)
                ghash.update(chunk)

        # return the hex representation of digest
        return ghash.hexdigest()
