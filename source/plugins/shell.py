import sys
import os
import subprocess

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import print_help_line


def print_help():
    print_help_line(0, "Daedalus \"shell\" plugin help:")
    print_help_line(1, "help", "prints this description")
    print_help_line(1, "run ...", "executes the specified command in the default shell")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
    elif len(args) >= 2:
        if args[1] == "run":
            valid_command = True
            args.pop(0)
            args.pop(0)
            Shell.run(args)
    return valid_command


class Shell:
    def __init__(self):
        pass

    @classmethod
    def run(cls, args):
        command = ""
        for arg in args:
            command += arg + " "
        subprocess.call(command, shell=True)
