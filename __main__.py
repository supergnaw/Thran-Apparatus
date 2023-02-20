# --- CHECK REQUIRED PACKAGES --- #
import pkg_resources
required = {
    'opencv-python'
}
if required - {pkg.key for pkg in pkg_resources.working_set}:
    exit(f"Missing the following required packages: {required - {pkg.key for pkg in pkg_resources.working_set}}")

# ---- STANDARD IMPORTS ---- #
import argparse
import os
import json
import typing

# ---- CUSTOM CLASS IMPORTS ---- #
from ThranApparatus import ThranApparatus
from UpdateFromGit import UpdateFromGit

# ---- ARGUMENT PARSER ---- #
def argument_parser(json_arguments: typing.AnyStr = os.path.join(".", "config", "arguments.json")) -> bool | argparse.ArgumentParser:
    if not os.path.exists(json_arguments):
        print(f"{json_arguments} doesn't exist")
        return False
    with open(json_arguments) as f:
        args = json.loads(f.read())
    parser = argparse.ArgumentParser(description=args["description"])
    for arg in args["args"]:
        print(f"{arg['flag']}, --{arg['name']}")
        parser.add_argument(arg["flag"], f"--{arg['name']}", **args.get("kwargs", {}))
    return parser

# ---- MAIN SCRIPT ---- #
os.system("cls" if f"{os.name}" == "nt" else "clear")

if '__main__' == __name__:
    # Parse the arguments
    json_arguments = os.path.join(".", "config", "arguments.json")
    if not os.path.exists(json_arguments):
        exit(f"Configuration file '{json_arguments}' is missing")

    try:
        with open(json_arguments) as f:
            arguments = json.loads(f.read())
    except Exception as e:
        exit(f"Error reading {json_arguments} file: {e}")
    parser = argparse.ArgumentParser(description=arguments["description"])
    for arg in arguments["args"]:
        parser.add_argument(arg["flag"], f"--{arg['name']}", **arg.get("kwargs", {}))
    args = parser.parse_args()

    # Update all the things
    if args.update:
        github_repo_link = "https://api.github.com/repos/supergnaw/Thran-Apparatus/contents/"
        script_directory = os.path.dirname(os.path.abspath(__file__))
        updater = UpdateFromGit(github_repo_link, script_directory)
        updater.check()
        exit()

    # Show the script help
    if args.input is None:
        parser.print_help()
        exit()

    # Instantiate the thing
    TA = ThranApparatus(
        art_directory=args.art_directory,
        force_overwrite=args.force_overwrite,
        input=args.input,
        reminder=args.reminder,
        template=args.template,
        output=args.output,
        verbose=args.verbose,
        extra_options=args.extra_options
    )
