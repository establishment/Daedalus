import os
import sys
import subprocess
import json
from time import gmtime, strftime

import plugins.autossh
import plugins.hosts
import plugins.https
import plugins.nginx
import plugins.ssh
import plugins.sshconfig
import plugins.apply
import plugins.template
import config
from util import renew_env_var, apt_get, apt_update, ensure_json_exists
from meta_engine import MetaEngine

CURRENT_DAEDALUS_VERSION = "0.2.0"

KEY_DAEDALUS_VERSION = "DAEDALUS_VERSION"
KEY_DAEDALUS_ROOT = "DAEDALUS_ROOT"

DAEDALUS_ROOT = None
DAEDALUS_VERSION = None

print("")
command = ""
for arg in sys.argv:
    command += arg
    command += " "
print(strftime("%Y-%m-%d %H:%M:%S", gmtime()) + " executing command: " + command)


def install_daedalus():
    global DAEDALUS_ROOT

    apt_update()

    # directly needed by daedalus
    apt_get(["sed", "expect", "autossh", "sshpass", "letsencrypt", "curl"])

    # sysadmin tools
    apt_get(["vim", "htop"])

    # required for extract function in scripts/util.sh
    apt_get(["cabextract", "p7zip-full", "unrar"])

    # various compress utilities
    apt_get(["ncompress", "rar"])

    DAEDALUS_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    renew_env_var(KEY_DAEDALUS_ROOT, DAEDALUS_ROOT)
    renew_env_var(KEY_DAEDALUS_VERSION, CURRENT_DAEDALUS_VERSION)
    subprocess.call("rm /bin/daedalus > /dev/null 2>&1", shell=True)
    subprocess.call("cp " + DAEDALUS_ROOT + "/res/bin/daedalus /bin/daedalus", shell=True)
    subprocess.call("cp " + DAEDALUS_ROOT + "/res/bin/daedalus /bin/dad", shell=True)

    subprocess.call("rm /etc/init.d/daedalus > /dev/null 2>&1", shell=True)
    subprocess.call("cp " + DAEDALUS_ROOT + "/res/init.d/daedalus /etc/init.d/daedalus", shell=True)
    subprocess.call("chmod ugo+x /etc/init.d/daedalus", shell=True)
    subprocess.call("update-rc.d daedalus defaults", shell=True)

if len(sys.argv) == 2:
    if sys.argv[1] == "install":
        install_daedalus()
        print("Daedalus install completed!")
        exit(0)


def load_env():
    global DAEDALUS_VERSION
    DAEDALUS_VERSION = os.environ.get(KEY_DAEDALUS_VERSION)
    if os.environ.get("DAEDALUS_VERSION") is None:
        print("Daedalus is not installed!")
        exit(2)

    if DAEDALUS_VERSION != CURRENT_DAEDALUS_VERSION:
        print("Latest version of daedalus is " + CURRENT_DAEDALUS_VERSION)
        print("Your current configuration is using older version " + DAEDALUS_VERSION)
        print("Please run 'daedalus install' to update!")
        exit(2)

    global DAEDALUS_ROOT
    DAEDALUS_ROOT = os.environ.get(KEY_DAEDALUS_ROOT)
    if DAEDALUS_ROOT is None:
        print("DAEDALUS_ROOT is not set. Daedalus might have not been installed correctly ...")
        exit(2)


load_env()

config.Manager.set_root(DAEDALUS_ROOT)
config.Manager.load()

if config.Manager.is_in_project():
    engine = MetaEngine(DAEDALUS_ROOT, config.Manager.get_project())
else:
    engine = None


def get_metadata():
    metadata = {
        "daedalus": None,
        "autossh": plugins.autossh.AutoSSHManager.get_metadata(),
        "hosts": plugins.hosts.HostsManager.get_metadata()
    }
    if engine:
        metadata["daedalus"] = engine.get_metadata()
    return metadata


def print_help():
    print("Daedalus help:")
    print("\t\tNothing for now!")

valid_command = False
if len(sys.argv) == 1:
    print("Daedalus is here!")
    valid_command = True
elif len(sys.argv) == 2:
    if sys.argv[1] == "get-metadata":
        valid_command = True
        print(json.dumps(get_metadata()))
    elif sys.argv[1] == "help":
        valid_command = True
        print_help()
    elif sys.argv[1] == "upgrade":
        valid_command = True
        subprocess.call(DAEDALUS_ROOT + "/res/upgrade.sh")
elif len(sys.argv) == 3:
    if sys.argv[1] in ["deploy", "deploy-to", "install-on", "setup-machine"]:
        valid_command = True
        host_address = sys.argv[2]
        subprocess.call("daedalus ssh link root " + host_address, shell=True)
        subprocess.call("daedalus ssh deploy-to " + host_address + " " + DAEDALUS_ROOT + "/res/setup_new_machine.sh",
                        shell=True)

if valid_command:
    exit(0)


def check_plugin_return_code(return_code, plugin_name):
    if not return_code:
        print("Invalid plugin (" + plugin_name + ") command! Run \"daedalus " + plugin_name + " help\" for more info!")
        exit(2)
    else:
        exit(0)

if len(sys.argv) >= 2 and sys.argv[1] == "hosts":
    args = sys.argv.copy()
    args.pop(0)
    check_plugin_return_code(plugins.hosts.parse_command(args), sys.argv[1])

if len(sys.argv) >= 2 and sys.argv[1] == "autossh":
    args = sys.argv.copy()
    args.pop(0)
    check_plugin_return_code(plugins.autossh.parse_command(args), sys.argv[1])

if len(sys.argv) >= 2 and sys.argv[1] == "https":
    args = sys.argv.copy()
    args.pop(0)
    check_plugin_return_code(plugins.https.parse_command(args), sys.argv[1])

if len(sys.argv) >= 2 and sys.argv[1] == "ssh":
    args = sys.argv.copy()
    args.pop(0)
    check_plugin_return_code(plugins.ssh.parse_command(args), sys.argv[1])

if len(sys.argv) >= 2 and sys.argv[1] == "nginx":
    args = sys.argv.copy()
    args.pop(0)
    check_plugin_return_code(plugins.nginx.parse_command(args), sys.argv[1])

if len(sys.argv) >= 2 and sys.argv[1] in ["sshconfig", "sshconf"]:
    args = sys.argv.copy()
    args.pop(0)
    check_plugin_return_code(plugins.sshconfig.parse_command(args), sys.argv[1])

if len(sys.argv) >= 2 and sys.argv[1] == "apply":
    args = sys.argv.copy()
    args.pop(0)
    check_plugin_return_code(plugins.apply.parse_command(args), sys.argv[1])

if len(sys.argv) >= 2 and sys.argv[1] in ["template", "jinja2"]:
    args = sys.argv.copy()
    args.pop(0)
    check_plugin_return_code(plugins.template.parse_command(args), sys.argv[1])

if len(sys.argv) >= 2 and sys.argv[1] == "project":
    args = sys.argv.copy()
    args.pop(0)
    check_plugin_return_code(config.project_parse_command(args), "project")


def get_module_or_exit(name):
    module_obj = engine.module(name)
    if module_obj is None:
        print("could not find module <" + name + ">")
        exit(2)
    return module_obj


def module_exec(name, command, params=None):
    module = get_module_or_exit(name)
    if module.is_recursive(command):
        dependencies = engine.get_full_dependencies(name)
        dependencies.reverse()
        for dependence_name in dependencies:
            get_module_or_exit(dependence_name).run(command, params=params)
    else:
        module.run(command, params=params)


def ensure_engine():
    if not engine:
        print("MetaEngine: you are not currently in any project! Please switch to a project!")
        exit(2)

if len(sys.argv) >= 2 and sys.argv[1] in ["cfs", "configfs"]:
    ensure_engine()
    args = sys.argv.copy()
    args.pop(0)
    if engine.parse_configfs_command(args):
        exit(0)
    else:
        print("Invalid plugin (" + sys.argv[1] + ") command! Run \"daedalus " + sys.argv[1] + " help\" for more info!")
        exit(2)

if len(sys.argv) == 2:
    if sys.argv[1] == "startup":
        ensure_engine()
        valid_command = True
        plugins.autossh.AutoSSHManager.load_current_context()
        engine.startup()
    elif sys.argv[1] == "shutdown":
        ensure_engine()
        valid_command = True
        engine.shutdown()
    elif sys.argv[1] == "update":
        ensure_engine()
        valid_command = True
        engine.update_all(soft=True)
    elif sys.argv[1] == "update-version":
        ensure_engine()
        valid_command = True
        engine.update_all(soft=False)
    elif sys.argv[1] == "start":
        ensure_engine()
        valid_command = True
        engine.exec_on_all("start")
    elif sys.argv[1] in ["stop", "sync-stop"]:
        ensure_engine()
        valid_command = True
        engine.exec_reversed_on_all(sys.argv[1])
    elif sys.argv[1] == "restart":
        ensure_engine()
        valid_command = True
        engine.exec_reversed_on_all("sync-stop", filter_as=["restart"])
        engine.exec_on_all("start", filter_as=["restart"])
    elif sys.argv[1] == "force-restart":
        ensure_engine()
        valid_command = True
        engine.exec_reversed_on_all("force-stop")
        engine.exec_on_all("start")
    elif sys.argv[1] == "list-modules":
        ensure_engine()
        valid_command = True
        print("Available modules: " + str(engine.get_modules()))
    elif sys.argv[1] == "list-installed-modules":
        ensure_engine()
        valid_command = True
        print("Installed modules: " + str(engine.get_installed_modules()))
    elif sys.argv[1] == "info":
        ensure_engine()
        valid_command = True
        print("Available modules: " + str(engine.get_modules()))
        print("Installed modules: " + str(engine.get_installed_modules()))
        for module_name in engine.get_modules():
            print("-------------------------------")
            get_module_or_exit(module_name).info()
elif len(sys.argv) == 3:
    if sys.argv[1] == "info":
        ensure_engine()
        valid_command = True
        get_module_or_exit(sys.argv[2]).info()
    elif sys.argv[1] == "list-dependencies":
        ensure_engine()
        valid_command = True
        get_module_or_exit(sys.argv[2])
        dependencies = engine.get_full_dependencies(sys.argv[2])
        dependencies.reverse()
        print("Dependencies for module <" + str(sys.argv[2]) + ">: " + str(dependencies))
    elif sys.argv[1] in ["install", "purge", "reinstall", "update", "start", "stop", "restart", "startup"]:
        ensure_engine()
        valid_command = True
        module_exec(sys.argv[2], sys.argv[1])
    elif sys.argv[1] == "run":
        ensure_engine()
        valid_command = True
        engine.run_command(sys.argv[2])
elif len(sys.argv) == 4:
    if sys.argv[1] == "exec":
        ensure_engine()
        valid_command = True
        module_exec(sys.argv[2], sys.argv[3])
elif len(sys.argv) >= 5:
    if sys.argv[1] == "exec":
        ensure_engine()
        valid_command = True
        name = sys.argv[2]
        script = sys.argv[3]
        args = sys.argv.copy()
        args.pop(0)
        args.pop(0)
        args.pop(0)
        args.pop(0)
        module_exec(name, script, params=args)
    elif sys.argv[1] == "run":
        ensure_engine()
        valid_command = True
        script = sys.argv[2]
        args = sys.argv.copy()
        args.pop(0)
        args.pop(0)
        args.pop(0)
        engine.run_command(script, params=args)

if not valid_command:
    print("Invalid command! Run daedalus help for more info!")
