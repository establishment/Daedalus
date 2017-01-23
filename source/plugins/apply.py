import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import run


def print_help():
    print("Daedalus \"apply\" plugin help:")
    print("\t\tNothing for now!")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
    elif len(args) == 3:
        if args[1] == "sysctl":
            valid_command = True
            ApplyManager.sysctl(args[2])
        elif args[1] in ["security-limits", "securitylimits", "sec-limits", "sec-lims", "security-lims"]:
            valid_command = True
            ApplyManager.security_limits(args[2])
    return valid_command


class ApplyManager:
    @classmethod
    def sysctl(cls, path):
        run("cp " + path + " /etc/sysctl.conf")
        run("sysctl --system")

    @classmethod
    def security_limits(cls, path):
        run("cp " + path + " /etc/security/limits.conf")

