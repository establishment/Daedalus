import sys
import os
import subprocess

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

import config
from util import load_json, save_json, ensure_json_exists


def print_help():
    print("Daedalus \"autossh\" plugin help:")
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
        elif args[1] == "show":
            valid_command = True
            AutoSSHManager.load_current_context()
            autossh = AutoSSHManager()
            autossh.load()
            print(autossh.entries)
        elif args[1] == "apply":
            valid_command = True
            AutoSSHManager.load_current_context()
            autossh = AutoSSHManager()
            autossh.load()
            autossh.apply(overwrite=False)
        elif args[1] == "clear-tunnels":
            valid_command = True
            AutoSSHManager.load_current_context()
            AutoSSHManager.clear_tunnels()
    elif len(args) == 3:
        if args[1] == "delete-port":
            valid_command = True
            AutoSSHManager.load_current_context()
            autossh = AutoSSHManager()
            autossh.load()
            autossh.delete(mapped_port=args[2])
            autossh.save()
        elif args[1] == "delete-address":
            valid_command = True
            AutoSSHManager.load_current_context()
            autossh = AutoSSHManager()
            autossh.load()
            autossh.delete(mapped_address=args[2])
            autossh.save()
        elif args[1] == "apply" and (args[2] == "--overwrite" or args[2] == "--force"):
            valid_command = True
            AutoSSHManager.load_current_context()
            autossh = AutoSSHManager()
            autossh.load()
            autossh.apply(overwrite=True)
    elif len(args) == 4:
        if args[1] == "delete":
            valid_command = True
            AutoSSHManager.load_current_context()
            autossh = AutoSSHManager()
            autossh.load()
            autossh.delete(mapped_address=args[2], mapped_port=args[3])
            autossh.save()
    elif len(args) == 7:
        if args[1] == "add":
            valid_command = True
            AutoSSHManager.load_current_context()
            autossh = AutoSSHManager()
            autossh.load()
            autossh.add(args[2], args[3], args[4], args[5], args[6])
            autossh.save()
    return valid_command


class AutoSSHManager:
    default_path = None

    def __init__(self):
        self.entries = []

    @classmethod
    def get_metadata(cls):
        autossh = AutoSSHManager()
        autossh.load()
        data = {
            "entries": autossh.entries
        }
        return data

    @classmethod
    def load_current_context(cls):
        autossh_config_path = config.Manager.get_current_state_path() + "/autossh.json"
        ensure_json_exists(autossh_config_path)
        cls.set_default_path(autossh_config_path)

    def load(self, path=None):
        if not path:
            path = AutoSSHManager.default_path
        data = load_json(path)
        if "entries" in data:
            self.entries = data["entries"]
        else:
            self.entries = []

    def save(self, path=None):
        if not path:
            path = AutoSSHManager.default_path
        data = {
            "entries": self.entries
        }
        save_json(path, data)

    def apply(self, overwrite=False):
        if overwrite:
            AutoSSHManager.clear_tunnels()
        for entry in self.entries:
            AutoSSHManager.apply_entry(entry)

    def delete_by_port(self, mapped_port):
        new_entries = []
        for entry in self.entries:
            if entry["mapped_port"] == mapped_port:
                continue
            new_entries.append(entry)
        self.entries = new_entries

    def delete_by_address(self, mapped_address):
        new_entries = []
        for entry in self.entries:
            if entry["mapped_address"] == mapped_address:
                continue
            new_entries.append(entry)
        self.entries = new_entries

    def delete_entry(self, mapped_address, mapped_port):
        new_entries = []
        for entry in self.entries:
            if entry["mapped_port"] == mapped_port and entry["mapped_address"] == mapped_address:
                continue
            new_entries.append(entry)
        self.entries = new_entries

    def delete(self, mapped_port=None, mapped_address=None):
        if not mapped_port and not mapped_address:
            return
        elif not mapped_port:
            self.delete_by_address(mapped_address)
        elif not mapped_address:
            self.delete_by_port(mapped_port)
        else:
            self.delete_entry(mapped_address, mapped_port)

    def add(self, mapped_port, mapped_address, remote_port, remote_user, remote_host):
        self.delete(mapped_port, mapped_address)
        self.entries.append({
            "mapped_port": mapped_port,
            "mapped_address": mapped_address,
            "remote_port": remote_port,
            "remote_user": remote_user,
            "remote_host": remote_host
        })

    @classmethod
    def clear_tunnels(cls):
        subprocess.call("killall autossh > /dev/null 2>&1", shell=True)

    @classmethod
    def set_default_path(cls, path):
        cls.default_path = path

    @classmethod
    def apply_entry(cls, entry):
        cls.autossh(entry["mapped_port"], entry["mapped_address"], entry["remote_port"], entry["remote_user"],
                    entry["remote_host"])

    @classmethod
    def autossh(cls, mapped_port, mapped_address, remote_port, remote_user, remote_host):
        command = "autossh -f -N -L " + mapped_port + ":" + mapped_address + ":" + remote_port
        command += " " + remote_user + "@" + remote_host
        subprocess.call(command, shell=True)
