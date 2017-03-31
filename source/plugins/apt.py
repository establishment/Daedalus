import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import run, print_help_line


def print_help():
    print_help_line(0, "Daedalus \"apt\" plugin help:")
    print_help_line(1, "help", "print this description")
    print_help_line(1, "update", "update apt repositories")
    print_help_line(1, "dist-upgrade", "runs dist-upgrade in force-mode (no interactivity)")
    print_help_line(1, "install <package>", "install the specified package (--yes by default)")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
        elif args[1] == "update":
            valid_command = True
            AptManager.update()
        elif args[1] == "dist-upgrade":
            valid_command = True
            AptManager.dist_upgrade()
    elif len(args) == 3:
        if args[1] == "install":
            valid_command = True
            AptManager.install(args[2])
    return valid_command


class AptManager:
    @classmethod
    def install(cls, package, force_yes=True):
        cmd = "sudo apt-get install "
        if force_yes:
            cmd += " -y "
        cmd += package
        run(cmd)

    @classmethod
    def update(cls):
        run("sudo apt-get update")

    @classmethod
    def dist_upgrade(cls, force_yes=True):
        if force_yes:
            run("sudo " + os.environ.get("DAEDALUS_ROOT") + "/tools/bash/force_apt_dist_upgrade.sh")
        else:
            run("sudo apt-get dist-upgrade")

