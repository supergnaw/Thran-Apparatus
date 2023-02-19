# --- CHECK REQUIRED PACKAGES --- #
import UpdateFromGit

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
import os

# --- CUSTOM IMPORTS --- #
import ThranApparatus
from UpdateFromGit import UpdateFromGit

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

    # Update all the things
    if args.update:
        github_repo_link = "https://api.github.com/repos/supergnaw/Thran-Apparatus/contents/"
        script_directory = os.path.dirname(os.path.abspath(__file__))
        updater = UpdateFromGit(github_repo_link, script_directory)
        updater.check()
        updater.show()
        exit()

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
