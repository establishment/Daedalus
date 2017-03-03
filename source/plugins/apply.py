import sys
import os
import subprocess

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import run, print_help_line


def print_help():
    print_help_line(0, "Daedalus \"apply\" plugin help:")
    print_help_line(1, "help", "print this description")
    print_help_line(1, "git-submodule-hooks", "apply helper hooks for git submodule (tools/git-submodule-hooks) to " +
                    "the current git from the working directory")
    print_help_line(1, "sysctl <path/to/file>", "overwrites and apply sysctl settings from config file at path/to/file")
    print_help_line(1, "{security-limits, securitylimits, sec-limits, sec-lims, security-lims}",
                    "overwrites and apply security limits from config file at path/to/file")
    print_help_line(1, "set-hostname", "change current machine hostname")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
        elif args[1] == "git-submodule-hooks":
            valid_command = True
            subprocess.call("cd " + os.environ.get("DAEDALUS_WORKING_DIRECTORY") + "; " +
                            os.environ.get("DAEDALUS_ROOT") + "/tools/git-submodule-hooks/install.sh", shell=True)
    elif len(args) == 3:
        if args[1] == "sysctl":
            valid_command = True
            ApplyManager.sysctl(args[2])
        elif args[1] in ["security-limits", "securitylimits", "sec-limits", "sec-lims", "security-lims"]:
            valid_command = True
            ApplyManager.security_limits(args[2])
        elif args[1] == "set-hostname":
            valid_command = True
            ApplyManager.set_hostname(args[2])
    return valid_command


class ApplyManager:
    @classmethod
    def sysctl(cls, path):
        run("cp " + path + " /etc/sysctl.conf")
        run("sysctl --system")

    @classmethod
    def security_limits(cls, path):
        run("cp " + path + " /etc/security/limits.conf")

    @classmethod
    def set_hostname(cls, hostname):
        run(os.environ.get("DAEDALUS_ROOT") + "/tools/bash/set_hostname.sh " + hostname)
