import sys
import os
import stat
import copy

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
        json_include = copy.deepcopy(JSONInclude.get(get_real_path(path)))
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
    def compile_header(cls, json_include, run_on=None):
        return "#!/usr/bin/env bash\n\n"

    @classmethod
    def compile_init(cls, json_include, run_on=None, priority=None):
        script = ""
        if "init" in json_include.data:
            script = cls.compile_command_block(json_include.data["init"], run_on=run_on, priority=priority)
        return cls.lazy_new_line(script)

    @classmethod
    def compile_project_setup(cls, json_include, run_on=None):
        script = ""
        if "project" in json_include.data:
            if "name" in json_include.data["project"]:
                if "path" in json_include.data["project"]:
                    command = "daedalus project add " + json_include.data["project"]["name"] + " " + \
                              json_include.data["project"]["path"]
                    script += cls.compile_run_on(command, run_on) + "\n"
                command = "daedalus project switch " + json_include.data["project"]["name"]
                script += cls.compile_run_on(command, run_on) + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_https(cls, json_include, run_on=None):
        script = ""
        if "https" in json_include.data:
            for entry in json_include.data["https"]:
                if "email" in json_include.data["https"][entry]:
                    script += cls.compile_run_on("daedalus https new-ssl " + entry + " " +
                                                 json_include.data["https"][entry]["email"], run_on) + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_configfs(cls, json_include, run_on=None):
        script = ""
        if "configfs" in json_include.data:
            for key in json_include.data["configfs"]:
                if type(json_include.data["configfs"][key]) is list:
                    for list_el in json_include.data["configfs"][key]:
                        script += cls.compile_run_on("daedalus configfs insert " + key + " " + escape_arg(list_el),
                                                     run_on) + "\n"
                elif json_include.data["configfs"][key] is None:
                    script += cls.compile_run_on("daedalus configfs request-private " + key, run_on) + "\n"
                else:
                    script += cls.compile_run_on("daedalus configfs set " + key + " " +
                                                 escape_arg(str(json_include.data["configfs"][key])), run_on) + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_modules(cls, json_include, run_on=None):
        script = ""
        if "modules" in json_include.data:
            for module in json_include.data["modules"]:
                if json_include.data["modules"][module] == "latest":
                    command = "daedalus install " + module
                    script += cls.compile_run_on(command, run_on) + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_commands(cls, commands, run_on=None):
        script = ""
        for command in commands:
            script += cls.compile_run_on("daedalus " + command, run_on) + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def command_block_get_all_priorities(cls, command_block):
        priorities = []
        for entry in command_block:
            if "priority" not in entry:
                continue
            if "commands" not in entry:
                continue
            priorities.append(entry["priority"])
        return sorted(set(priorities))

    @classmethod
    def compile_command_block(cls, command_block, run_on=None, priority=None):
        script = ""
        if priority is None:
            priorities = cls.command_block_get_all_priorities(command_block)
            for target_priority in priorities:
                script += cls.compile_command_block(command_block, priority=target_priority, run_on=run_on)
        else:
            for entry in command_block:
                if "priority" not in entry:
                    continue
                if "commands" not in entry:
                    continue
                current_run_on = run_on
                if "ignoreRunOn" in entry:
                    if entry["ignoreRunOn"]:
                        current_run_on = None
                if priority == entry["priority"]:
                    script += cls.compile_commands(entry["commands"], run_on=current_run_on)
        return script

    @classmethod
    def compile_post_install(cls, json_include, run_on=None, priority=None):
        script = ""
        if "postInstall" in json_include.data:
            script = cls.compile_command_block(json_include.data["postInstall"], run_on=run_on, priority=priority)
        return cls.lazy_new_line(script)

    @classmethod
    def compile_hosts(cls, json_include, run_on=None):
        script = ""
        if "hosts" in json_include.data:
            for host in json_include.data["hosts"]:
                if "privateIP" in json_include.data["hosts"][host]:
                    command = "daedalus hosts add " + host + " " + \
                              str(json_include.data["hosts"][host]["privateIP"])
                    script += cls.compile_run_on(command, run_on) + "\n"
                elif "publicIP" in json_include.data["hosts"][host]:
                    command = "daedalus hosts add " + host + " " + \
                              str(json_include.data["hosts"][host]["publicIP"])
                    script += cls.compile_run_on(command, run_on) + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_ssh_link(cls, json_include, run_on=None):
        script = ""
        if "sshLink" in json_include.data:
            for host in json_include.data["sshLink"]:
                command = "daedalus ssh link " + json_include.data["sshLink"][host]["remoteUser"] + " " + \
                          json_include.data["sshLink"][host]["remoteHost"] + " " + \
                          json_include.data["sshLink"][host]["sshKey"]
                script += cls.compile_run_on(command, run_on) + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_autossh(cls, json_include, run_on=None):
        script = ""
        if "autossh" in json_include.data:
            for entry in json_include.data["autossh"]:
                command = "daedalus autossh add " + str(json_include.data["autossh"][entry]["localPort"]) + " " + \
                          json_include.data["autossh"][entry]["localHost"] + " " + \
                          str(json_include.data["autossh"][entry]["remotePort"]) + " " + \
                          json_include.data["autossh"][entry]["remoteUser"] + " " + \
                          json_include.data["autossh"][entry]["remoteHost"]
                script += cls.compile_run_on(command, run_on) + "\n"
            if script != "":
                script += cls.compile_run_on("daedalus autossh apply --overwrite", run_on) + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_post_ssh_link(cls, json_include, run_on=None, priority=None):
        script = ""
        if "postSSHLink" in json_include.data:
            script = cls.compile_command_block(json_include.data["postSSHLink"], run_on=run_on, priority=priority)
        return cls.lazy_new_line(script)

    @classmethod
    def write_script(cls, save_path, script):
        with open(save_path, "w") as save_file:
            save_file.write(script)
        st = os.stat(save_path)
        os.chmod(save_path, st.st_mode | stat.S_IEXEC)

    @classmethod
    def replace_bulk(cls, val, replace_array):
        temp = val
        for entry in replace_array:
            if entry["to"] is None:
                to = ""
            else:
                to = entry["to"]
            temp = temp.replace(entry["from"], to)
        return temp

    @classmethod
    def translate_context(cls, val):
        replace_array = []
        state = 0
        payload = ""
        for i, c in enumerate(val):
            if c == "C" and state == 0:
                state = 1
            elif c == ">" and state == 1:
                state = 2
            elif c == "{" and state == 2:
                state = 3
                payload = ""
            elif c == "}" and state == 3:
                state = 0
                content = None
                if payload in cls.context:
                    content = cls.context[payload]
                replace_array.append({"from": "C>{" + payload + "}", "to": content})
            elif state == 3:
                payload += c
        val = cls.replace_bulk(val, replace_array)
        return val

    @classmethod
    def resolve_context(cls, data):
        for k, v in data.items():
            if isinstance(data[k], list):
                temp = []
                for val in data[k]:
                    if isinstance(val, dict):
                        cls.resolve_context(val)
                        temp.append(val)
                    else:
                        temp.append(cls.translate_context(val))
                data[k] = temp
            elif isinstance(data[k], dict):
                cls.resolve_context(data[k])
            elif isinstance(data[k], str):
                data[k] = cls.translate_context(data[k])

    @classmethod
    def get_json_param(cls, param, path, work_dir=None, this=None):
        if path == "this":
            data = this
        else:
            data = load_json(get_real_path(path, work_dir=work_dir))
        if "params" not in data:
            return None
        if param not in data["params"]:
            return None
        return data["params"][param]

    @classmethod
    def translate_params(cls, val, work_dir=None, this=None):
        replace_array = []
        state = 0
        payload = ""
        for i, c in enumerate(val):
            if c == "P" and state == 0:
                state = 1
            elif c == ">" and state == 1:
                state = 2
            elif c == "{" and state == 2:
                state = 3
                payload = ""
            elif c == "}" and state == 3:
                state = 0
                if "@" not in payload:
                    param = payload
                    path = "this"
                else:
                    tokens = payload.split("@")
                    if len(tokens) != 2:
                        continue
                    param = tokens[0]
                    path = tokens[1]
                replace_array.append({"from": "P>{" + payload + "}", "to": cls.get_json_param(param, path,
                                                                                              work_dir=work_dir,
                                                                                              this=this)})
            elif state == 3:
                payload += c
        val = cls.replace_bulk(val, replace_array)
        return val

    @classmethod
    def resolve_params(cls, data, work_dir=None, this=None):
        for k, v in data.items():
            if isinstance(data[k], list):
                temp = []
                for val in data[k]:
                    if isinstance(val, dict):
                        cls.resolve_params(val, work_dir=work_dir, this=this)
                        temp.append(val)
                    else:
                        temp.append(cls.translate_params(val, work_dir=work_dir, this=this))
                data[k] = temp
            elif isinstance(data[k], dict):
                cls.resolve_params(data[k])
            elif isinstance(data[k], str):
                data[k] = cls.translate_params(data[k], work_dir=work_dir, this=this)

    @classmethod
    def translate_env_vars(cls, val, work_dir=None, this=None):
        replace_array = []
        state = 0
        payload = ""
        for i, c in enumerate(val):
            if c == "E" and state == 0:
                state = 1
            elif c == ">" and state == 1:
                state = 2
            elif c == "{" and state == 2:
                state = 3
                payload = ""
            elif c == "}" and state == 3:
                state = 0
                env = os.environ.copy()
                env.update(config.Manager.get_env())
                content = env.get(payload, None)
                replace_array.append({"from": "E>{" + payload + "}", "to": content})
            elif state == 3:
                payload += c
        val = cls.replace_bulk(val, replace_array)
        return val

    @classmethod
    def resolve_env_vars(cls, data):
        for k, v in data.items():
            if isinstance(data[k], list):
                temp = []
                for val in data[k]:
                    if isinstance(val, dict):
                        cls.resolve_env_vars(val)
                        temp.append(val)
                    else:
                        temp.append(cls.translate_env_vars(val))
                data[k] = temp
            elif isinstance(data[k], dict):
                cls.resolve_env_vars(data[k])
            elif isinstance(data[k], str):
                data[k] = cls.translate_env_vars(data[k])

    @classmethod
    def compile_machine(cls, json_include, save_path=None, work_dir=None, add_header=True, run_on=None):
        if add_header:
            script = cls.compile_header(json_include, run_on=run_on)
        else:
            script = ""
        script += cls.compile_init(json_include, run_on=run_on)
        script += cls.compile_project_setup(json_include, run_on=run_on)
        script += cls.compile_https(json_include, run_on=run_on)
        script += cls.compile_configfs(json_include, run_on=run_on)
        script += cls.compile_modules(json_include, run_on=run_on)
        script += cls.compile_post_install(json_include, run_on=run_on)
        script += cls.compile_hosts(json_include, run_on=run_on)
        script += cls.compile_ssh_link(json_include, run_on=run_on)
        script += cls.compile_autossh(json_include, run_on=run_on)
        script += cls.compile_post_ssh_link(json_include, run_on=run_on)
        if save_path is not None:
            cls.write_script(save_path, script)
        return script

    @classmethod
    def compile_run_on(cls, command, host=None):
        if host:
            return "daedalus ssh run " + host + " " + escape_arg(command)
        return command

    @classmethod
    def compile_cluster_standalone(cls, json_include, save_path=None, work_dir=None):
        script = cls.compile_header(json_include)
        if "machines" in json_include.data:
            for entry in json_include.data["machines"]:
                if "address" not in entry:
                    continue
                if "description" not in entry:
                    continue
                machine_json_include = cls.load_description(get_real_path(entry["description"], work_dir=work_dir))
                script += cls.compile_machine(machine_json_include, work_dir=work_dir, add_header=False,
                                              run_on=entry["address"]) + "\n"
        if save_path is not None:
            cls.write_script(save_path, script)
        return script

    @classmethod
    def compile_master_pair(cls, machine_json_include):
        script = ""
        if "sshLink" in machine_json_include.data:
            print(machine_json_include.data["sshLink"])
            for entry in machine_json_include.data["sshLink"]:
                from_user = "root"
                from_address = machine_json_include.data["params"]["hostPublicIP"]
                to_user = machine_json_include.data["sshLink"][entry]["remoteUser"]
                to_address = machine_json_include.data["sshLink"][entry]["remotePublicIP"]
                ssh_key = machine_json_include.data["sshLink"][entry]["sshKey"]
                script += "daedalus ssh pair " + from_user + " " + from_address + " " + to_user + " " + \
                          to_address + " " + ssh_key + "\n"
        return cls.lazy_new_line(script)

    @classmethod
    def compile_cluster_master(cls, json_include, save_path=None, work_dir=None):
        script = cls.compile_header(json_include)
        machines = []
        if "machines" in json_include.data:
            for entry in json_include.data["machines"]:
                if "address" not in entry:
                    continue
                if "description" not in entry:
                    continue
                print(cls.load_description(get_real_path(entry["description"], work_dir=work_dir)).data["sshLink"])
                machines.append({
                    "machine": cls.load_description(get_real_path(entry["description"], work_dir=work_dir)),
                    "address": entry["address"]
                })
        print("***********")

        all_priorities = []
        for machine in machines:
            machine_json_include = machine["machine"]
            if "init" in machine_json_include.data:
                all_priorities += cls.command_block_get_all_priorities(machine_json_include.data["init"])
        all_priorities = sorted(set(all_priorities))
        for priority in all_priorities:
            for machine in machines:
                machine_json_include = machine["machine"]
                script += cls.compile_init(machine_json_include, run_on=machine["address"], priority=priority)

        for machine in machines:
            machine_json_include = machine["machine"]
            script += cls.compile_project_setup(machine_json_include, run_on=machine["address"])
            script += cls.compile_https(machine_json_include, run_on=machine["address"])
            script += cls.compile_configfs(machine_json_include, run_on=machine["address"])
            script += cls.compile_modules(machine_json_include, run_on=machine["address"])

        all_priorities = []
        for machine in machines:
            machine_json_include = machine["machine"]
            if "postInstall" in machine_json_include.data:
                all_priorities += cls.command_block_get_all_priorities(machine_json_include.data["postInstall"])
        all_priorities = sorted(set(all_priorities))
        for priority in all_priorities:
            for machine in machines:
                machine_json_include = machine["machine"]
                script += cls.compile_post_install(machine_json_include, run_on=machine["address"], priority=priority)

        for machine in machines:
            machine_json_include = machine["machine"]
            script += cls.compile_hosts(machine_json_include, run_on=machine["address"])

        # SSH LINK
        for machine in machines:
            machine_json_include = machine["machine"]
            script += cls.compile_master_pair(machine_json_include)

        all_priorities = []
        for machine in machines:
            machine_json_include = machine["machine"]
            if "postSSHLink" in machine_json_include.data:
                all_priorities += cls.command_block_get_all_priorities(machine_json_include.data["postSSHLink"])
        all_priorities = sorted(set(all_priorities))
        for priority in all_priorities:
            for machine in machines:
                machine_json_include = machine["machine"]
                script += cls.compile_post_ssh_link(machine_json_include, run_on=machine["address"], priority=priority)

        if save_path is not None:
            cls.write_script(save_path, script)
        return script

    @classmethod
    def compile_cluster(cls, json_include, save_path=None, work_dir=None):
        if json_include.data["deployType"] == "standalone":
            return cls.compile_cluster_standalone(json_include, save_path=save_path, work_dir=work_dir)
        elif json_include.data["deployType"] == "master":
            return cls.compile_cluster_master(json_include, save_path=save_path, work_dir=work_dir)

    @classmethod
    def load_description(cls, path, work_dir=None):
        json_include = copy.deepcopy(JSONInclude.get(get_real_path(path)))
        cls.resolve_params(json_include.data, work_dir=work_dir, this=json_include.data)
        cls.resolve_context(json_include.data)
        cls.resolve_env_vars(json_include.data)
        return json_include

    @classmethod
    def compile(cls, path, save_path=None):
        work_dir = os.path.dirname(path)
        if not work_dir.startswith("/"):
            work_dir = None
        json_include = cls.load_description(path, work_dir=work_dir)
        if json_include.data["type"] == "machine":
            return cls.compile_machine(json_include, save_path=save_path, work_dir=work_dir)
        elif json_include.data["type"] == "cluster":
            return cls.compile_cluster(json_include, save_path=save_path, work_dir=work_dir)
