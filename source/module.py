import os
import subprocess

from util import load_json, get_files_in, run, escape_arg
from configfs import ConfigFS


class Module:
    command_ignore_on_fail = ["startup", "shutdown", "start", "stop", "update"]

    def __init__(self, name, root_dir, env=None, custom_config_path=None,
                custom_config_modules_dir=None, custom_config_module_dir=None,
                namespace=None):
        self.namespace = None
        self.available_namespaces = []

        if env:
            self.env = env.copy()
        else:
            self.env = None
        self.root_dir = root_dir
        self.config_fs = ConfigFS(os.path.join(self.env["DAEDALUS_STATE_PATH"], "configfs"))
        self.name = name

        self.config_plugin_name = None
        if "." in self.name:
            self.config_plugin_name = self.name.split(".")[0]

        if custom_config_path:
            self.config_path = custom_config_path
        else:
            self.config_path = self.env["DAEDALUS_CONFIG_PATH"]

        if custom_config_modules_dir:
            self.config_modules_dir = custom_config_modules_dir
        elif self.env["DAEDALUS_CONFIG_MODULES_PATH"]:
            self.config_modules_dir = self.env["DAEDALUS_CONFIG_MODULES_PATH"]
        else:
            self.config_modules_dir = os.path.join(self.config_path, "modules")

        if custom_config_module_dir:
            self.config_module_dir = custom_config_module_dir
        elif self.env["DAEDALUS_STATE_MODULE_PATH"]:
            self.config_module_dir = self.env["DAEDALUS_STATE_MODULE_PATH"]
        else:
            self.config_module_dir = os.path.join(self.config_modules_dir, name)
        
        self.state_module_dir = os.path.join(self.env["DAEDALUS_STATE_MODULES_PATH"], name)
        
        self.env["DAEDALUS_CONFIG_PLUGIN_NAME"] = self.config_plugin_name
        self.env["DAEDALUS_CONFIG_PATH"] = self.config_path
        self.env["DAEDALUS_CONFIG_MODULES_PATH"] = self.config_modules_dir
        self.env["DAEDALUS_CONFIG_MODULE_PATH"] = self.config_module_dir
        self.env["DAEDALUS_STATE_MODULE_PATH"] = self.state_module_dir
        self.env["DAEDALUS_MODULE_NAME"] = self.name
        
        self.desc = None

        self.scripts = self.load_module_scripts()

        self.version = None
        self.module = None
        self.scripts = None
        self.dependencies = None

        description_file = self.config_module_dir + "/description.json"
        if not os.path.isfile(description_file):
            self.log("Error: Module \"" + self.name + "\" does not have a description file!")
        else:
            self.parse_description(load_json(description_file))

        self.set_namespace(namespace)

    def get_metadata(self):
        data = {
            "rawModuleName": self.name,
            "descriptionFile": self.desc,
            "installedVersion": self.config_fs.get(self.desc["module"] + "-version")
        }
        return data

    def load_module_scripts(self):
        config_path = self.config_module_dir + "/scripts"
        if not os.path.isdir(config_path):
            return []
        return get_files_in(config_path)

    def parse_description(self, desc):
        self.desc = desc
        if "version" not in self.desc:
            self.log("Error: Description of module \"" + self.name + "\" does not have a version field")
            return
        else:
            self.version = self.desc["version"]

        if "module" not in self.desc:
            self.log("Error: Description of module \"" + self.name + "\" does not have a module field")
            return
        else:
            self.module = self.desc["module"]

        if "scripts" not in self.desc:
            self.log("Error: Description of module \"" + self.name + "\" does not have a scripts field")
            return

        if "dependencies" in self.desc:
            self.dependencies = []
            for dependency in self.desc["dependencies"]:
                if "." in dependency:
                    self.dependencies.append(dependency)
                else:
                    if self.config_plugin_name is not None:
                        dependency = self.config_plugin_name + "." + dependency
                    self.dependencies.append(dependency)

    def get_this_tag(self):
        if self.namespace:
            return self.name + "#" + self.namespace
        return self.name

    def log(self, message):
        print("<" + self.get_this_tag() + ">: " + message)

    def get_scripts(self):
        return self.scripts

    def get_name(self):
        return self.name

    def get_path(self):
        return self.config_module_dir

    def get_description(self):
        return self.desc

    def get_dependencies(self):
        if self.dependencies is None:
            return []
        return self.dependencies

    @classmethod
    def str_to_priority(cls, priority):
        if type(priority) is int:
            return priority
        priority = priority.upper()
        if priority == "FIRST":
            return -500
        elif priority == "LAST":
            return 500
        return 0

    def get_priority(self, command):
        script_data = self.search_script_by_alias(command)
        if script_data is None:
            return 0
        if "priority" not in script_data:
            return 0
        return Module.str_to_priority(script_data["priority"])

    def search_script_by_alias(self, script):
        for script_data in self.desc["scripts"]:
            if "aliases" in script_data:
                for alias in script_data["aliases"]:
                    if alias == script:
                        return script_data
        return None

    def check_dependencies(self, dependencies):
        for key in dependencies:
            if key == "<this>":
                key = self.get_this_tag()
            elif "." not in key and self.config_plugin_name:
                key = self.config_plugin_name + "." + key
            if not self.config_fs.exists(key):
                return False
        return True

    def is_outdated(self):
        module_name = self.desc["module"]
        if self.config_plugin_name:
            module_name = self.config_plugin_name + "." + module_name
        return self.config_fs.get(module_name + "-version") != self.desc["version"]

    def purge(self):
        self.config_fs.delete(self.desc["module"] + "-version")
        subprocess.call("rm -rf " + self.state_module_dir, shell=True)
        if self.search_script_by_alias("purge") is not None:
            return self.run("purge", internal=True)
        return 0

    # TODO: error in state-modifying code is a bit tricky. 
    # No safeguards yet, so no need to treat reinstall carefully!
    def reinstall(self, force=False):
        if force or self.is_outdated():
            self.run("purge")
            self.run("install")
        return 0

    def restart(self):
        rc = self.run("sync-stop")
        if rc != 0:
            return rc
        return self.run("start")

    def force_restart(self):
        rc = self.run("force-stop")
        if rc != 0:
            return rc
        return self.run("start")

    def startup(self):
        if self.search_script_by_alias("startup") is not None:
            return self.run("startup", internal=True)
        return 0

    def shutdown(self):
        if self.search_script_by_alias("shutdown") is not None:
            return self.run("shutdown", internal=True)
        return 0

    def info(self):
        print("Raw module name: " + self.desc["module"])
        if self.desc is None:
            print("Description file: No")
            return
        else:
            print("Description file: Yes")
        print("Module alias: " + self.name)
        print("Latest version: " + self.desc["version"])
        installed_version_key = self.name + "-version"
        if "<this>" not in self.available_namespaces and self.available_namespaces:
            installed_version_key += "#" + self.available_namespaces[0]
        installed_version = self.config_fs.get(installed_version_key)
        if installed_version is not None:
            print("Installed version: " + installed_version)
            print("Available namespaces: " + str(self.available_namespaces))
        else:
            print("Installed version: N/A")

    def is_recursive(self, script):
        script_data = self.search_script_by_alias(script)
        if script_data is None:
            return False
        if "isRecursive" not in script_data:
            return False
        return script_data["isRecursive"]

    def is_singleton(self):
        if "isSingleton" not in self.desc:
            return False
        return self.desc["isSingleton"]

    def set_namespace(self, namespace):
        if namespace == "<this>" or self.is_singleton():
            self.namespace = None
        else:
            self.namespace = namespace

    def is_install_script(self, script):
        script_data = self.search_script_by_alias(script)
        if script_data is None:
            return False
        if "isInstallScript" not in script_data:
            return False
        return script_data["isInstallScript"]

    @classmethod
    def run_error(cls):
        # TODO: maybe not exit like a spoiled little kid and actually try to fix?
        exit(2)

    def run(self, script, internal=False, params=None):
        script_params = params
        script_data = self.search_script_by_alias(script)
        if script_data is None:
            if script == "reinstall":
                return self.reinstall()
            elif script == "update":
                if not internal:
                    return self.run("reinstall", internal=True)
                return 0
            elif script == "purge":
                if not internal:
                    return self.purge()
                return 0
            elif script in ["sync-stop", "force-stop"]:
                return self.run("stop")
            elif script == "startup":
                if not internal:
                    return self.startup()
                return 0
            elif script == "shutdown":
                if not internal:
                    return self.shutdown()
                return 0
            elif script == "restart":
                return self.restart()
            elif script == "force-restart":
                return self.force_restart()
            elif script in Module.command_ignore_on_fail:
                self.log("Warning: \"" + script + "\" command is not " + 
                         "defined for this module! Going to ignore!")
                return 0
            else:
                self.log("Error: <" + self.name + namespace_str + "> does not contain " +
                         "any script with alias \"" + script + "\"")
                self.run_error()

        if script == "update":
            rc = self.run("reinstall", internal=True)
            if rc != 0:
                return rc

        file_name = None
        if "file" in script_data:
            file_name = script_data["file"]

        params = None
        if "params" in script_data:
            params = script_data["params"]
            if not isinstance(params, list):
                params = [params]

        dependencies = None
        if "dependencies" in script_data:
            dependencies = script_data["dependencies"]

        is_install_script = False
        if "isInstallScript" in script_data:
            is_install_script = script_data["isInstallScript"]

        installed_version_key = self.name + "-version"
        if self.namespace:
            installed_version_key += "#" + self.namespace
       
        if is_install_script:
            installed_version = self.config_fs.get(installed_version_key)
            if installed_version is not None:
                if self.namespace:
                    self.log("Module \"" + self.name + "\" is already " + 
                             "available for namespace \"" + self.namespace + 
                             "\"! Installed version: " + installed_version)
                else:
                    self.log("Module \"" + self.name + "\" is already installed! " + 
                             "Installed version: " + installed_version)
                if self.desc["version"] == installed_version:
                    self.log("You already have the latest version!")
                    # Everything is fine when we have the latest version so we should return 0
                    return 0
                else:
                    self.log("Latest version is: " + self.desc["version"] + 
                             " Run reinstall (or purge and install)!")
                    # TODO: right now the flow would not be interrupted when older 
                    # module version is installed.
                    
                    # Maybe prompt for user input?
                    return 0
            else:
                namespace_state_module_dir = self.state_module_dir
                if self.namespace:
                    namespace_state_module_dir += "#" + self.namespace
                os.makedirs(namespace_state_module_dir, exist_ok=True)
        else:
            if self.namespace and self.namespace not in self.available_namespaces:
                self.log("Error: <" + self.name + "> does not have namespace \"" + 
                         self.namespace + "\" installed!")
                exit(2)

        param_values = ""
        if params is not None:
            for param in params:
                default_value = None
                if ":" in param:
                    tokens = param.split(":")
                    param = tokens[0]
                    default_value = tokens[1]
                    for index in range(2, len(tokens)):
                        default_value += ":"
                        default_value += tokens[index]
                is_global = False
                use_namespace = True
                if ">" in param:
                    tokens = param.split(">")
                    param = tokens[1]
                    selector = tokens[0].upper()
                    if "G" in selector:
                        is_global = True
                    elif "L" in selector:
                        is_global = False
                    if "M" in selector:
                        use_namespace = True
                    if "S" in selector:
                        use_namespace = False
                if not is_global and self.config_plugin_name is not None:
                    param = self.config_plugin_name + "." + param
                if use_namespace and self.namespace is not None:
                    if self.config_fs.exists(param + "#" + self.namespace):
                        param += "#" + self.namespace
                param_value = self.config_fs.get(param)
                if param_value is None and default_value is None:
                    self.log("Error: command \"" + script + "\" (" + file_name + 
                             ") requires configfs parameter \"" + param + "\"")
                    self.run_error()
                elif param_value is None and default_value is not None:
                    param_value = default_value
                    self.log("Warning: command \"" + script + "\" (" + file_name + 
                             ") requires configfs parameter \"" +
                             param + "\". Setting it to default value: " + default_value)
                    self.config_fs.set(param, default_value)
                param_values += " "
                param_values += escape_arg(param_value)
        if dependencies is not None:
            if not self.check_dependencies(dependencies):
                self.log("Error: command \"" + script + "\" (" + file_name + 
                         ") depends on: " + str(dependencies))
                self.run_error()

        command = "sudo -E " + self.root_dir + "/tools/bash/run_from_path.sh " + self.env["DAEDALUS_PROJECT_PATH"] + " "
        command += self.config_module_dir + "/scripts/" + file_name
        command += param_values
        params = script_params
        if params is not None:
            for param in params:
                command += " "
                command += escape_arg(param)

        env = self.env
        env["DAEDALUS_MODULE_COMMAND"] = script
        namespace = ""
        namespace_suffix = ""
        if self.namespace is not None:
            namespace = self.namespace
            namespace_suffix = "#" + self.namespace
        env["DAEDALUS_MODULE_NAMESPACE"] = namespace
        env["DAEDALUS_FULL_STATE_MODULE_PATH"] = self.state_module_dir + namespace_suffix
        env["DAEDALUS_FULL_MODULE_NAME"] = self.name + namespace_suffix
        rc = run(command, env=env)

        if is_install_script:
            self.config_fs.set(installed_version_key, self.desc["version"])
            self.log("Installation complete!")
        else:
            self.log("Command \"" + script + "\" done!")

        return rc
