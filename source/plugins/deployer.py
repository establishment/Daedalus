import sys
import os
import stat
parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import print_help_line, get_real_path, escape_arg
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
    elif len(args) == 3:
        if args[1] == "preprocess":
            valid_command = True
            print(Deployer.preprocess(args[2]))
        elif args[1] == "compile":
            valid_command = True
            print(Deployer.compile(args[2]))
    elif len(args) == 4:
        if args[1] == "preprocess":
            valid_command = True
            Deployer.preprocess(args[2], args[3])
        elif args[1] == "compile":
            valid_command = True
            Deployer.compile(args[2], args[3])
    return valid_command


class Deployer:
    def __init__(self):
        self.entries = []

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
                    script += "daedalus project add " + json_include.data["project"]["name"] + " " + json_include.data["project"]["path"] + "\n"
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
                    script += "daedalus hosts add " + host + " " + json_include.data["hosts"][host]["privateIP"] + "\n"
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
    def compile(cls, path, save_path=None):
        json_include = JSONInclude.get(get_real_path(path))
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
