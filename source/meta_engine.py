import os

import config
import plugins.autossh
from util import get_dirs_in, get_files_in, load_json, ensure_password, format_two_column, run
from module import Module
from configfs import ConfigFS
from graph import Graph


class MetaEngine:
    def __init__(self, root_dir, project):
        self.env = config.Manager.get_env(project)
        self.root_dir = root_dir
        self.project_state_path = self.env["DAEDALUS_STATE_PATH"]
        self.project = project
        self.module_names = []
        self.modules = {}
        self.installed_modules = []
        self.configfs_path = os.path.join(self.project_state_path, "configfs")
        self.configfs = ConfigFS(self.configfs_path)
        self.dependencies_graph = Graph()

        self.reload()

    def get_metadata(self):
        data = {}
        modules_data = []
        for module_name in self.get_modules():
            modules_data.append(self.module(module_name).get_metadata())
        data["modules"] = modules_data
        return data

    @staticmethod
    def filter_modules_by_name(modules):
        filtered_modules = []
        for module in modules:
            if not module.endswith("-old") and not module.endswith("-deprecated"):
                filtered_modules.append(module)
        return filtered_modules

    @staticmethod
    def filter_installed_modules(configfs_vars):
        installed_modules = []
        for var in configfs_vars:
            if var.endswith("-version"):
                installed_modules.append(var[:-len("-version")])
        return installed_modules

    def update_all(self, soft=True):
        if soft:
            self.exec_on_all("update")
        else:
            self.exec_on_all("stop")
            self.exec_on_all("reinstall")
            self.exec_on_all("start")

    def get_bulk_command_filter(self, filter_as):
        command_filters = []
        for filter_command in filter_as:
            this_filters = self.configfs.list.get("option-ignore-on-bulk-" + filter_command)
            if this_filters:
                command_filters += this_filters
        if command_filters is None:
            command_filters = []
        final_command_filters = []
        for command_filter in command_filters:
            final_command_filters.append(command_filter.upper())
        return final_command_filters

    def exec_on_all(self, command, filter_as=None):
        module_names = self.sorted_by_command_priority_installed_modules(command)
        if not filter_as:
            filter_as = []
        filter_as.append(command)
        command_filter = self.get_bulk_command_filter(filter_as)
        filtered_module_names = []
        for module_name in module_names:
            if module_name.upper() not in command_filter:
                filtered_module_names.append(module_name)
        self.exec_in_order(filtered_module_names, command)

    def exec_reversed_on_all(self, command, filter_as=None):
        module_names = self.sorted_by_command_priority_installed_modules(command)
        module_names.reverse()
        if not filter_as:
            filter_as = []
        filter_as.append(command)
        command_filter = self.get_bulk_command_filter(filter_as)
        filtered_module_names = []
        for module_name in module_names:
            if module_name.upper() not in command_filter:
                filtered_module_names.append(module_name)
        self.exec_in_order(filtered_module_names, command)

    def exec_in_order(self, module_names, command):
        for module_name in module_names:
            self.module(module_name).run(command)

    def startup(self):
        autossh_on_boot = self.get_config_key("autossh-on-boot")
        if autossh_on_boot is not None:
            if autossh_on_boot.upper() == "TRUE":
                autossh = plugins.autossh.AutoSSHManager()
                autossh.load()
                autossh.apply()

        module_name_list = self.sorted_installed_modules()
        for module_name in module_name_list:
            self.module(module_name).startup()

        start_on_boot = self.get_config_key("start-on-boot")
        if start_on_boot is not None:
            if start_on_boot.upper() == "TRUE":
                self.exec_on_all("start")

    def shutdown(self):
        self.exec_reversed_on_all("stop")

        module_name_list = self.sorted_installed_modules()
        module_name_list.reverse()
        for module_name in module_name_list:
            self.module(module_name).shutdown()

    def load_module_list(self):
        config_path = self.env["DAEDALUS_CONFIG_MODULES_PATH"]
        modules = get_dirs_in(config_path)
        return self.filter_modules_by_name(modules)

    def load_installed_modules(self):
        os.makedirs(self.configfs_path, exist_ok=True)
        return self.filter_installed_modules(get_files_in(self.configfs_path))

    @classmethod
    def sort_modules(cls, modules, order):
        ordered_modules = []
        modules = [module.upper() for module in modules]
        for module in order:
            if module.upper() in modules:
                ordered_modules.append(module)
        return ordered_modules

    def get_priority(self, module, command):
        module_obj = self.module(module)
        if not module_obj:
            return 0
        return module_obj.get_priority(command)

    def order_by_command_priority(self, command):
        ordered_modules = []
        graph_order = self.dependencies_graph.topo_sort_all()
        sorted_modules = []
        index = 0
        for module in graph_order:
            index += 1
            sorted_modules.append([module, self.get_priority(module, command), index])
        sorted_modules = sorted(sorted_modules, key=lambda x: (x[1], x[2]))
        for module in sorted_modules:
            ordered_modules.append(module[0])
        return ordered_modules

    def sorted_installed_modules(self):
        return MetaEngine.sort_modules(self.load_installed_modules(), self.dependencies_graph.topo_sort_all())

    def sorted_by_command_priority_installed_modules(self, command):
        return MetaEngine.sort_modules(self.load_installed_modules(), self.order_by_command_priority(command))

    def reload(self):
        self.module_names = [name.lower() for name in self.load_module_list()]
        for module_name in self.module_names:
            self.modules[module_name] = Module(module_name, self.root_dir, self.env)
            module_dependencies = self.modules[module_name].get_dependencies()
            self.dependencies_graph.add_node(module_name)
            for module_dependence in module_dependencies:
                self.dependencies_graph.add_edge(module_dependence, module_name)
        self.installed_modules = [name.lower() for name in self.load_installed_modules()]

        for module_name in self.module_names:
            module_dependencies = self.modules[module_name].get_dependencies()
            for module_dependence in module_dependencies:
                if module_dependence not in self.module_names:
                    print("Error: invalid configuration! Module \"" + module_name +
                          "\" depends on invalid module \"" + module_dependence + "\"")
                    exit(1)

        cycle = self.dependencies_graph.check_for_cycle()
        if cycle:
            print("Error: invalid configuration! There is a cycle in the dependencies graph!")
            print("Cycle: " + str(cycle))
            exit(1)

    def get_modules(self):
        return self.module_names

    def module(self, name):
        name = name.lower()
        if name not in self.modules:
            return None
        return self.modules[name]

    def get_installed_modules(self):
        return self.installed_modules

    @staticmethod
    def is_internal_key(key):
        return key.endswith("-version") or key.endswith("-internal")

    def get_config_keys(self):
        return self.configfs.get_all_keys()

    def get_config_key(self, key):
        return self.configfs.get(key)

    def get_full_dependencies(self, module_name):
        return self.dependencies_graph.topo_sort(module_name)

    def run_command(self, command):
        final_command = "sudo -E " + self.root_dir + "/tools/bash/run_from_path.sh " + \
                        self.env["DAEDALUS_PROJECT_PATH"] + " " + self.env["DAEDALUS_CONFIG_PATH"] + "/scripts/" + \
                        command
        return run(final_command, env=self.env)

    def print_configfs_help(self):
        print("ConfigFS: Nothing for now!")

    def parse_configfs_command(self, args):
        valid_command = False
        if len(args) == 1:
            valid_command = True
            self.print_configfs_help()
        elif len(args) == 2:
            if args[1] == "help":
                valid_command = True
                self.print_configfs_help()
            elif args[1] == "show-all":
                valid_command = True
                keys = self.configfs.get_all_keys()
                for key in keys:
                    value = self.configfs.get(key)
                    print(format_two_column(key, str(value), 80))
            elif args[1] == "show-config":
                valid_command = True
                keys = self.configfs.get_all_keys()
                for key in keys:
                    if not MetaEngine.is_internal_key(key):
                        value = self.configfs.get(key)
                        print(format_two_column(key, str(value), 80))
            elif args[1] == "delete-all":
                valid_command = True
                keys = self.configfs.get_all_keys()
                for key in keys:
                    self.configfs.delete(key)
                    print("Delete config key \"" + key + "\"")
            elif args[1] == "delete-config":
                valid_command = True
                keys = self.configfs.get_all_keys()
                for key in keys:
                    if not MetaEngine.is_internal_key(key):
                        self.configfs.delete(key)
                        print("Delete config key \"" + key + "\"")
        elif len(args) == 3:
            if args[1] == "delete":
                valid_command = True
                self.configfs.delete(args[2])
            elif args[1] == "delete-list":
                valid_command = True
                self.configfs.list.delete(args[2])
            elif args[1] == "exists":
                valid_command = True
                if self.configfs.exists(args[2]):
                    print("Yes")
                else:
                    print("No")
            elif args[1] == "exists-list":
                valid_command = True
                if self.configfs.list.exists(args[2]):
                    print("Yes")
                else:
                    print("No")
            elif args[1] in ["request-pw", "request-private", "request-hidden"]:
                valid_command = True
                value = ensure_password("Please insert the value for ConfigFS field \"" + args[2] + "\"!")
                self.configfs.set(args[2], value)
            elif args[1] == "show":
                valid_command = True
                value = self.configfs.get(args[2])
                if value is not None:
                    print(value)
                else:
                    print("Error: There is no key named \"" + args[2] + "\"")
            elif args[1] == "show-list":
                valid_command = True
                value = self.configfs.list.get(args[2])
                if value is not None:
                    print(value)
                else:
                    print("Error: There is not list named \"" + args[2] + "\"")
        elif len(args) == 4:
            if args[1] == "set":
                valid_command = True
                self.configfs.set(args[2], args[3])
            elif args[1] == "set-list":
                valid_command = True
                self.configfs.list.set(args[2], args[3])
            elif args[1] == "contains":
                valid_command = True
                if self.configfs.list.contains(args[2], args[3]):
                    print("Yes")
                else:
                    print("No")
            elif args[1] == "remove":
                valid_command = True
                self.configfs.list.remove(args[2], args[3])
            elif args[1] == "insert":
                valid_command = True
                self.configfs.list.insert(args[2], args[3])
        return valid_command
