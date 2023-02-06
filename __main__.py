# --- CHECK REQUIRED PACKAGES --- #

required = {
    'opencv-python'
}
import pkg_resources

installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed

if missing:
    print(f"Missing the following required packages: {missing}")
    exit()

# --- STANDARD IMPORTS --- #
import argparse
import hashlib
import requests
import os
from typing import AnyStr

# --- CUSTOM IMPORTS --- #
import ThranApparatus


# --- UPDATING FUNCTIONS --- #
def check_for_updates() -> None:
    response = requests.get("https://api.github.com/repos/supergnaw/Thran-Apparatus/contents/")

    for f in json.loads(response.text):
        file_name, download_url, remote_hash = f["path"], f["download_url"], f["sha"]

        # It's a new file
        if not os.path.exists(f["path"]):
            update_file(f["path"], f["download_url"])

        if f["sha"] != file_git_hash(f["path"]):
            print(f"File is different ({file_name}) - local: {file_git_hash(file_name)} | remote: {remote_hash}")
            update_file(file_name, download_url)


def update_file(target_file, raw_link) -> bool:
    allowed_updates = ['replus.py']

    if os.path.exists(target_file) and target_file not in allowed_updates:
        print(f"File update disallowed: {target_file}")
        return False

    print(0, f"Updating file: {target_file}")

    response = requests.get(raw_link)
    if 200 != response.status_code:
        verbose(0, f"Update failed: status code {response.status_code} received.")
        return False

    # with open(target_file, "wb") as f:
    #     f.write(response.content)
    print(f"Successfully updated {target_file}")

    return True


def file_git_hash(filename: AnyStr) -> str:
    """"This function returns the SHA-1 hash
    of the file passed into it"""
    # read only 1024 bytes at a time
    byte_limit = 1024
    ghash = hashlib.sha1()
    ghash.update(f"blob {os.stat(filename).st_size}\0".encode("utf-8"))

    # open file for reading in binary mode
    with open(filename, 'rb') as file:
        chunk = 0
        while chunk != b'':
            chunk = file.read(byte_limit)
            ghash.update(chunk)

    # return the hex representation of digest
    return ghash.hexdigest()


# --- SCRIPT ARGUMENTS --- #
DEFAULT_ART_DIRECTORY = f'.{os.path.sep}art{os.path.sep}original'
DEFAULT_TEMPLATE = 'classicRedux'
DEFAULT_OUTPUT_DIRECTORY = f'.{os.path.sep}renders'


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='A python-based Magic: The Gathering playtest card image generator.')
    parser.add_argument('-a', '--art-directory', metavar='string', default=DEFAULT_ART_DIRECTORY,
                        help=f'Directory containing card art images (Default: "{DEFAULT_ART_DIRECTORY}")')
    parser.add_argument('-f', '--force-overwrite', action='store_true', default=False,
                        help='Force image overwriting when generating new card images (Default: False)')
    parser.add_argument('-i', '--input', metavar='string', default=None,
                        help='Input list of card images to render')
    parser.add_argument('-r', '--reminder', action='store_true', default=False,
                        help='Include available reminder text (Default: False)')
    parser.add_argument('-t', '--template', nargs=1, metavar='string', default=DEFAULT_TEMPLATE,
                        help=f'Template name (Default: "{DEFAULT_TEMPLATE}")')
    parser.add_argument('-o', '--output', nargs=1, metavar='string', default=DEFAULT_OUTPUT_DIRECTORY,
                        help=f'Write output to directory (Default: "{DEFAULT_OUTPUT_DIRECTORY}")')
    parser.add_argument('-u', '--update', action='store_true', default=False,
                        help='Update script and local database (Default: False)')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Show more information during card list processing')
    parser.add_argument('-x', '--extra-options', nargs='+', default=[],
                        help="Extra options for templates with additional positional settings")
    return parser


# --- MAIN SCRIPT --- #
os.system("cls" if f"{os.name}" == "nt" else "clear")

if '__main__' == __name__:
    parser = argument_parser()
    args = parser.parse_args()

    # Update the everything
    if args.update:
        check_for_updates()

    # Show the script help
    if args.input is None:
        parser.print_help()
        exit()

    # Instantiate the thing
    TA = ThranApparatus.ThranApparatus(
        art_directory=args.art_directory,
        force_overwrite=args.force_overwrite,
        input=args.input,
        reminder=args.reminder,
        template=args.template,
        output=args.output,
        verbose=args.verbose,
        extra_options=args.extra_options
    )
