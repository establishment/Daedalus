import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

import config
from util import load_json, save_json, ensure_json_exists, print_help_line


def print_help():
    print_help_line(0, "Daedalus \"config manager\" plugin help:")
    print_help_line(1, "help", "prints this description")
    print_help_line(1, "list", "displays all installed config plugins")
    print_help_line(1, "remove <plugin-name>", "removes the link to the specified plugin")
    print_help_line(1, "add <plugin-name> <path/to/plugin>", "register the specified path as the specified plugin name if it is not already registered")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
        elif args[1] == "list":
            valid_command = True
            ConfigPluginManager.load()
            for name in ConfigPluginManager.config_plugins_data:
                print(name)
    elif len(args) == 3:
        if args[1] == "remove":
            valid_command = True
            ConfigPluginManager.load()
            ConfigPluginManager.remove(args[2])
            ConfigPluginManager.save()
    elif len(args) == 4:
        if args[1] == "add":
            valid_command = True
            ConfigPluginManager.load()
            ConfigPluginManager.add(args[2], args[3])
            ConfigPluginManager.save()
    return valid_command


class ConfigPluginManager:
    config_plugins_path = None
    config_plugins_data = {}

    @classmethod
    def load_current_context(cls):
        cls.config_plugins_path = config.Manager.get_global_state_path() + "/config_plugins.json"
        ensure_json_exists(cls.config_plugins_path)

    @classmethod
    def load(cls):
        if not cls.config_plugins_path:
            cls.load_current_context()
        cls.config_plugins_data= load_json(cls.config_plugins_path)

    @classmethod
    def add(cls, name, path):
        if name in cls.config_plugins_data:
            print("Error: there already exists a config plugin with name \"" + name + "\"")
            exit(2)
        cls.config_plugins_data[name] = {
            "path": path 
        }

    @classmethod
    def remove(cls, name):
        if not name in cls.config_plugins_data:
            print("Error: there is no such config plugin configured with name \"" + name + "\"")
            exit(2)
        del cls.config_plugins_data[name]

    @classmethod
    def save(cls):
        if not cls.config_plugins_path:
            cls.load_current_context()
        save_json(cls.config_plugins_path, cls.config_plugins_data)

