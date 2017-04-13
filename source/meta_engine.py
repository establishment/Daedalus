import os

import config
import plugins.autossh
from util import load_json, ensure_json_exists, get_dirs_in, get_files_in, ensure_password, format_two_column, run, print_help_line
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

        self.config_plugin_db = os.path.join(self.env["DAEDALUS_GLOBAL_STATE_PATH"], "config_plugins.json")
        self.config_plugins = {}

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
            module = self.module(module_name)
            for namespace in module.available_namespaces:
                module.namespace = namespace
                if module.namespace == "<this>":
                    module.namespace = None
                module.run(command)

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
        modules = [name.lower() for name in get_dirs_in(config_path)]

        ensure_json_exists(self.config_plugin_db)
        config_plugins_data = load_json(self.config_plugin_db)
        for config_plugin_name in config_plugins_data:
            config_plugin_data = config_plugins_data[config_plugin_name]
            if "path" not in config_plugin_data:
                print("Warning: invalid config-plugin data. Entry \"" + config_plugin_name + 
                      "\" does not contain field 'path'! Skipping ...")
                continue
            self.config_plugins[config_plugin_name] = config_plugin_data
            modules_path = os.path.join(config_plugin_data["path"], "modules")
            modules += [config_plugin_name + "." + name.lower() for name in get_dirs_in(modules_path)]
        modules = self.filter_modules_by_name(modules)
        return modules

    def split_module_name(self, full_module_name):
        tokens = full_module_name.split(".")
        if len(tokens) == 1:
            config_plugin_name = None
            module_name = tokens[0].lower()
        elif len(tokens) == 2:
            config_plugin_name = tokens[0].lower()
            module_name = tokens[1].lower()
        else:
            print("Error: Invalid full module name: " + full_module_name)
            exit(1)
        return config_plugin_name, module_name

    def get_module_data(self, full_module_name):
        config_plugin_name, module_name = self.split_module_name(full_module_name)
        if config_plugin_name:
            config_path = self.config_plugins[config_plugin_name]["path"]
            config_modules_dir = os.path.join(config_path, "modules")
            config_module_dir = os.path.join(config_modules_dir, module_name)
        else:
            config_path = self.env["DAEDALUS_CONFIG_PATH"]
            config_modules_dir = self.env["DAEDALUS_CONFIG_MODULES_PATH"]
            config_module_dir = os.path.join(config_modules_dir, module_name)
        return config_path, config_modules_dir, config_module_dir

    def load_installed_modules(self):
        os.makedirs(self.configfs_path, exist_ok=True)
        configfs_vars = get_files_in(self.configfs_path)
        installed_modules = []
        for var in configfs_vars:
            namespace = None
            if "#" in var:
                tokens = var.split("#")
                var = tokens[0]
                namespace = tokens[1]
            if var.endswith("-version"):
                module_name = var[:-len("-version")]
                installed_modules.append(module_name)
                if namespace:
                    self.modules[module_name].available_namespaces.append(namespace)
                else:
                    self.modules[module_name].available_namespaces.append("<this>")
        self.installed_modules = installed_modules
        return installed_modules

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
        return MetaEngine.sort_modules(self.get_installed_modules(),
                                       self.dependencies_graph.topo_sort_all())

    def sorted_by_command_priority_installed_modules(self, command):
        return MetaEngine.sort_modules(self.get_installed_modules(),
                                       self.order_by_command_priority(command))

    def reload(self):
        self.module_names = self.load_module_list()
        for module_name in self.module_names:
            config_path, config_modules_dir, config_module_dir = self.get_module_data(module_name)
            self.modules[module_name] = Module(module_name, self.root_dir, env=self.env,
                                            custom_config_path=config_path,
                                            custom_config_modules_dir=config_modules_dir,
                                            custom_config_module_dir=config_module_dir)
        
        self.load_installed_modules()

        for module_name in self.module_names:
            self.dependencies_graph.add_node(module_name)

        for module_name in self.module_names:
            module_dependencies = self.modules[module_name].get_dependencies()
            for module_dependence in module_dependencies:
                self.dependencies_graph.add_edge(module_dependence, module_name)

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
        namespace = None
        if "#" in name:
            tokens = name.split("#")
            name = tokens[0].lower()
            namespace = tokens[1]
        name = name.lower()
        if name not in self.modules:
            return None
        self.modules[name].namespace = namespace
        return self.modules[name]

    def get_installed_modules(self):
        return self.installed_modules

    @staticmethod
    def is_internal_key(key):
        if "#" in key:
            key = key.split("#")[0]
        return key.endswith("-version") or key.endswith("-internal")

    def get_config_keys(self):
        return self.configfs.get_all_keys()

    def get_config_key(self, key):
        return self.configfs.get(key)

    def get_full_dependencies(self, module_name):
        namespace = None
        if "#" in module_name:
            tokens = module_name.split("#")
            module_name = tokens[0].lower()
            namespace = tokens[1]
        return self.dependencies_graph.topo_sort(module_name), namespace

    def run_command(self, command, params=None):
        params_line = ""
        if params:
            for param in params:
                params_line += " " + param
        final_command = "sudo -E " + self.root_dir + "/tools/bash/run_from_path.sh " + \
                        self.env["DAEDALUS_PROJECT_PATH"] + " " + self.env["DAEDALUS_CONFIG_PATH"] + "/scripts/" + \
                        command + params_line
        return run(final_command, env=self.env)

    @staticmethod
    def print_configfs_help():
        print_help_line(0, "Daedalus Config File System submodule:")
        print_help_line(1, "help", "prints this description")
        print_help_line(1, "show-all",
                        "prints everything stored in the current configfs session (including internal data)")
        print_help_line(1, "show-config", "prints every user-defined settings stored in the current configfs session")
        print_help_line(1, "delete-all", "delete all settings stored (including internal data)")
        print_help_line(1, "delete-config", "delete all user-defined settings")
        print_help_line(1, "delete <key>", "delete the key-value pair associated with key")
        print_help_line(1, "delete-list <list_key>", "delete the key-list pair associated with key")
        print_help_line(1, "exists <key>", "check if there is a key-value pair associated with key")
        print_help_line(1, "exists-list <list_key>", "check if there is a key-list pair associated with key")
        print_help_line(1, "{request-pw, request-private, request-hidden} <key>",
                        "request hidden user input from console the set key with private data")
        print_help_line(1, "show <key>", "prints the value associated with key")
        print_help_line(1, "show-list <list_key>", "prints the list associated with key")
        print_help_line(1, "set <key> <value>", "sets the pair key-value")
        print_help_line(1, "set-list <list_key> <value>", "sets delete the current list with key list_key and sets " +
                        "it to a new list containing only value as a single element")
        print_help_line(1, "contains <list_key> <value>",
                        "prints yes or no if list_key contains or not an element with value")
        print_help_line(1, "remove <list_key> <value>",
                        "remove the element value from the list associated with the key")
        print_help_line(1, "insert <list_key> <value>",
                        "insert a new element value in list associated with the key")
        print_help_line(0, "Every command accepting <key> as argument will switch to the list counter-part command " +
                        "when the key starts with the prefix \"list:\"")

    def parse_configfs_command(self, args):
        valid_command = False
        if len(args) == 1:
            valid_command = True
            MetaEngine.print_configfs_help()
        elif len(args) == 2:
            if args[1] == "help":
                valid_command = True
                self.print_configfs_help()
            elif args[1] == "show-all":
                valid_command = True
                keys = self.configfs.get_all_keys()
                keys.sort()
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
