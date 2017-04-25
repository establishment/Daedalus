import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

import config
from util import load_json, save_json, ensure_json_exists, print_help_line, run


def print_help():
    print_help_line(0, "Daedalus \"config manager\" plugin help:")
    print_help_line(1, "help", "prints this description")
    print_help_line(1, "list", "displays all installed config plugins")
    print_help_line(1, "remove <plugin-name>", "removes the link to the specified plugin")
    print_help_line(1, "add <plugin-name> <path/to/plugin>", "register the specified path as the specified plugin name if it is not already registered")
    print_help_line(1, "install <git-url>", "install the config plugin at the specified git repository")
    print_help_line(1, "uninstall <git-url>", "uninstall the config plugin at the specified git repository")
    print_help_line(1, "update <git-url>", "update the config plugin at the specified git repository")
    print_help_line(1, "{update-all, update}", "update all the config plugins installed via git repository")


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
        elif args[1] in ["update-all", "update"]:
            valid_command = True
            ConfigPluginManager.load()
            ConfigPluginManager.update_all()
            ConfigPluginManager.save()
    elif len(args) == 3:
        if args[1] == "remove":
            valid_command = True
            ConfigPluginManager.load()
            ConfigPluginManager.remove(args[2])
            ConfigPluginManager.save()
        elif args[1] == "install":
            valid_command = True
            ConfigPluginManager.load()
            ConfigPluginManager.install(args[2])
            ConfigPluginManager.save()
        elif args[1] == "uninstall":
            valid_command = True
            ConfigPluginManager.load()
            ConfigPluginManager.uninstall(args[2])
            ConfigPluginManager.save()
        elif args[1] == "update":
            ConfigPluginManager.load()
            ConfigPluginManager.update(args[2])
            ConfigPluginManager.save()
        elif args[1] == "add":
            ConfigPluginManager.load()
            ConfigPluginManager.add_from_path(args[2])
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
        cls.config_plugins_data = load_json(cls.config_plugins_path)

    @classmethod
    def add(cls, name, path):
        if name in cls.config_plugins_data:
            print("Error: there already exists a config plugin with name \"" + name + "\"")
            exit(2)
        cls.config_plugins_data[name] = {
            "path": path
        }

    @classmethod
    def add_from_path(cls, path):
        if not os.path.isfile(path + "/description.json"):
            print("Error: there is no description.json file at the specified location!")
            exit(2)
        config_plugin_description = load_json(path + "/description.json")
        cls.add(config_plugin_description["name"], path)

    @classmethod
    def remove(cls, name):
        if not name in cls.config_plugins_data:
            print("Error: there is no such config plugin configured with name \"" + name + "\"")
            exit(2)
        del cls.config_plugins_data[name]

    @classmethod
    def normalize_git_url(cls, git_url):
        if len(git_url.split("/")) == 2:
            git_url = "https://github.com/" + git_url
        return git_url

    @classmethod
    def find_plugin_by_path(cls, path):
        for config_plugin_name in cls.config_plugins_data:
            config_plugin_data = cls.config_plugins_data[config_plugin_name]
            if config_plugin_data["path"] == path:
                return config_plugin_name
        return None

    @classmethod
    def find_plugin_by_git_url(cls, git_url):
        for config_plugin_name in cls.config_plugins_data:
            config_plugin_data = cls.config_plugins_data[config_plugin_name]
            if "gitUrl" in config_plugin_data:
                if config_plugin_data["gitUrl"] == git_url:
                    return config_plugin_name
        return None

    @classmethod
    def get_folder_name_from_git_url(cls, git_url):
        tokens = git_url.split("/")
        name = ""
        for token in tokens:
            if token.startswith("http") or token == "":
                continue
            if name != "":
                name += "."
            name += token
        return name

    @classmethod
    def install(cls, git_url):
        git_url = cls.normalize_git_url(git_url)
        if cls.find_plugin_by_git_url(git_url):
            print("ConfigManager: Plugin at " + git_url + " is already installed!")
            exit(2)
        path = config.Manager.get_global_state_path() + "/config_plugins"
        run("mkdir -p \"" + path + "\"")
        path_to_repo = path + "/" + cls.get_folder_name_from_git_url(git_url)
        run("cd \"" + path + "\"; git clone " + git_url + " " + path_to_repo)
        cls.add_from_path(path_to_repo)

    @classmethod
    def uninstall(cls, git_url):
        git_url = cls.normalize_git_url(git_url)
        config_plugin_name = cls.find_plugin_by_git_url(git_url)
        if config_plugin_name is None:
            print("ConfigManager: Plugin " + git_url + " is not installed!")
            exit(2)
        run("rm -rf " + cls.config_plugins_data[config_pugin_name]["path"])
        del cls.config_plugins_data[config_plugin_name]

    @classmethod
    def update_safe(cls, config_plugin_name):
        path = cls.config_plugins_data[config_plugin_name]["path"]
        run("cd \"" + path + "\"; git pull")

    @classmethod
    def update(cls, git_url):
        git_url = cls.normalize_git_url(git_url)
        config_plugin_name = cls.find_plugin_by_git_url(git_url)
        if config_plugin_name is None:
            print("ConfigManager: Plugin " + git_url + " is not installed!")
            exit(2)
        cls.update_safe(config_plugin_name)

    @classmethod
    def update_all(cls):
        for config_plugin_name in cls.config_plugins_data:
            config_plugin_data = cls.config_plugins_data[config_plugin_name]
            if "gitUrl" in config_plugin_data:
                cls.update_safe(config_plugin_name)

    @classmethod
    def save(cls):
        if not cls.config_plugins_path:
            cls.load_current_context()
        save_json(cls.config_plugins_path, cls.config_plugins_data)

