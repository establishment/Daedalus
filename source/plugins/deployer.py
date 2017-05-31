import sys
import os
import stat

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

import config
from util import print_help_line, get_real_path, escape_arg, ensure_json_exists, load_json, save_json
from json_include import JSONInclude


def print_help():
    print_help_line(0, "Daedalus \"deployer\" plugin help:")
    print_help_line(1, "help", "prints this description")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
        elif args[1] == "get-context-path":
            valid_command = True
            Deployer.load_settings()
            print(Deployer.settings.get("pathToContext", None))
        elif args[1] == "get-context":
            valid_command = True
            Deployer.load_context()
            print(Deployer.context)
    elif len(args) == 3:
        if args[1] == "preprocess":
            valid_command = True
            Deployer.load_context()
            print(Deployer.preprocess(args[2]))
        elif args[1] == "compile":
            valid_command = True
            Deployer.load_context()
            print(Deployer.compile(args[2]))
        elif args[1] == "set-context":
            valid_command = True
            Deployer.load_settings()
            Deployer.set_context(args[2])
            Deployer.save_settings()
    elif len(args) == 4:
        if args[1] == "preprocess":
            valid_command = True
            Deployer.load_context()
            Deployer.preprocess(args[2], args[3])
        elif args[1] == "compile":
            valid_command = True
            Deployer.load_context()
            Deployer.compile(args[2], args[3])
    return valid_command


class Deployer:
    settings_default_path = None
    settings = {}
    context = {}

    def __init__(self):
        pass

    @classmethod
    def init_default_context(cls):
        autossh_config_path = config.Manager.get_current_state_path() + "/deployer.json"
        ensure_json_exists(autossh_config_path)
        cls.set_default_path(autossh_config_path)

    @classmethod
    def set_default_path(cls, path):
        cls.settings_default_path = path

    @classmethod
    def load_settings(cls, path=None):
        if not path:
            if cls.settings_default_path is None:
                cls.init_default_context()
            path = cls.settings_default_path
        cls.settings = load_json(path)

    @classmethod
    def save_settings(cls, path=None):
        if not path:
            if cls.settings_default_path is None:
                cls.init_default_context()
            path = cls.settings_default_path
        save_json(path, cls.settings)

    @classmethod
    def load_context(cls, path=None):
        if not path:
            cls.load_settings()
        if "pathToContext" in cls.settings:
            cls.context = load_json(cls.settings["pathToContext"])

    @classmethod
    def set_context(cls, path):
        cls.settings["pathToContext"] = get_real_path(path)

    @classmethod
    def preprocess(cls, path, save_path=None):
        json_include = JSONInclude.get(get_real_path(path))
        if save_path is not None:
            json_include.save(get_real_path(save_path))
        return json_include.data

    @classmethod
    def lazy_new_line(cls, text):
        if text != "":
            if text.endswith("\n\n"):
                return text
            return text + "\n"
        return text

    @classmethod
    def compile_header(cls, json_include):
        return "#!/usr/bin/env bash\n\n"

    @classmethod
    def compile_project_setup(cls, json_include):
        script = ""
        if "project" in json_include.data:
            if "name" in json_include.data["project"]:
                if "path" in json_include.data["project"]:
                    script += "daedalus project add " + json_include.data["project"]["name"] + " " + \
                              json_include.data["project"]["path"] + "\n"
                script += "daedalus project switch " + json_include.data["project"]["name"] + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_https(cls, json_include):
        script = ""
        if "https" in json_include.data:
            for entry in json_include.data["https"]:
                if "email" in json_include.data["https"][entry]:
                    script += ""
        return cls.lazy_new_line(script)

    @classmethod
    def compile_params(cls, json_include):
        script = ""
        if "params" in json_include.data:
            for key in json_include.data["params"]:
                if type(json_include.data["params"][key]) is list:
                    for list_el in json_include.data["params"][key]:
                        script += "daedalus configfs insert " + key + " " + escape_arg(list_el) + "\n"
                elif json_include.data["params"][key] is None:
                    script += "daedalus configfs request-private " + key + "\n"
                else:
                    script += "daedalus configfs set " + key + " " + escape_arg(str(json_include.data["params"][key])) \
                              + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_modules(cls, json_include):
        script = ""
        if "modules" in json_include.data:
            for module in json_include.data["modules"]:
                if json_include.data["modules"][module] == "latest":
                    script += "daedalus install " + module + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_commands(cls, commands):
        script = ""
        for command in commands:
            script += "daedalus " + command + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_post_install(cls, json_include):
        script = ""
        if "postInstall" in json_include.data:
            script = cls.compile_commands(json_include.data["postInstall"])
        return cls.lazy_new_line(script)

    @classmethod
    def compile_hosts(cls, json_include):
        script = ""
        if "hosts" in json_include.data:
            for host in json_include.data["hosts"]:
                if "privateIP" in json_include.data["hosts"][host]:
                    script += "daedalus hosts add " + host + " " + str(json_include.data["hosts"][host]["privateIP"]) + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_ssh_link(cls, json_include):
        script = ""
        if "sshLink" in json_include.data:
            for host in json_include.data["sshLink"]:
                script += "daedalus ssh link " + json_include.data["sshLink"][host]["remoteUser"] + " " + \
                          json_include.data["sshLink"][host]["remoteHost"] + " " + \
                          json_include.data["sshLink"][host]["sshKey"] + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_autossh(cls, json_include):
        script = ""
        if "autossh" in json_include.data:
            for entry in json_include.data["autossh"]:
                script += "daedalus autossh add " + str(json_include.data["autossh"][entry]["localPort"]) + " " + \
                          json_include.data["autossh"][entry]["localHost"] + " " + \
                          str(json_include.data["autossh"][entry]["remotePort"]) + " " + \
                          json_include.data["autossh"][entry]["remoteUser"] + " " + \
                          json_include.data["autossh"][entry]["remoteHost"] + "\n"
            if script != "":
                script += "daedalus autossh apply --overwrite\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_post_ssh_link(cls, json_include):
        script = ""
        if "postSSHLink" in json_include.data:
            script = cls.compile_commands(json_include.data["postSSHLink"])
        return cls.lazy_new_line(script)

    @classmethod
    def get_context_key(cls, key):
        if isinstance(key, str):
            if key.startswith("C>"):
                return key[2:]
        return None

    @classmethod
    def resolve_context(cls, data):
        for k, v in data.items():
            if isinstance(data[k], list):
                temp = []
                for val in data[k]:
                    var_key = cls.get_context_key(val)
                    if var_key:
                        if var_key in cls.context:
                            temp.append(cls.context[var_key])
                    else:
                        temp.append(val)
            elif isinstance(data[k], dict):
                cls.resolve_context(data[k])
            else:
                var_key = cls.get_context_key(v)
                if var_key:
                    if var_key in cls.context:
                        data[k] = cls.context[var_key]
                    else:
                        data[k] = None

    @classmethod
    def compile(cls, path, save_path=None):
        json_include = JSONInclude.get(get_real_path(path))
        cls.resolve_context(json_include.data)
        script = cls.compile_header(json_include)
        script += cls.compile_project_setup(json_include)
        script += cls.compile_https(json_include)
        script += cls.compile_params(json_include)
        script += cls.compile_modules(json_include)
        script += cls.compile_post_install(json_include)
        script += cls.compile_hosts(json_include)
        script += cls.compile_ssh_link(json_include)
        script += cls.compile_autossh(json_include)
        script += cls.compile_post_ssh_link(json_include)
        if save_path is not None:
            with open(save_path, "w") as save_file:
                save_file.write(script)
            st = os.stat(save_path)
            os.chmod(save_path, st.st_mode | stat.S_IEXEC)
        return script
