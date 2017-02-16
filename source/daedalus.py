import os
import sys
import subprocess
import json
import atexit
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
import filelock
from util import renew_env_var, apt_get, apt_update, id_generator, print_help_line
from meta_engine import MetaEngine

CURRENT_DAEDALUS_VERSION = "0.2.1"

KEY_DAEDALUS_VERSION = "DAEDALUS_VERSION"
KEY_DAEDALUS_ROOT = "DAEDALUS_ROOT"
KEY_DAEDALUS_FILE_LOCK_SESSION_UID = "DAEDALUS_FILE_LOCK_SESSION_UID"

DAEDALUS_ROOT = None
DAEDALUS_VERSION = None

print("")
command = ""
for arg in sys.argv:
    command += arg
    command += " "
print(strftime("[%Y-%m-%d %H:%M:%S]", gmtime()) + " executing command: " + command)

flock = None
session_uid = None


def exit_handler():
    global flock
    flock.release()


def start_session():
    global session_uid
    session_uid = os.environ.get(KEY_DAEDALUS_FILE_LOCK_SESSION_UID)
    if session_uid is None:
        session_uid = id_generator(32)
        os.environ[KEY_DAEDALUS_FILE_LOCK_SESSION_UID] = session_uid

    filelock_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state/file-lock/")
    filelock.FileLock.set_filelock_dir(filelock_dir)
    os.makedirs(filelock_dir, exist_ok=True)


def single_session():
    global flock

    flock = filelock.FileLock("daedalus", session_uid=session_uid, timeout=10)
    try:
        flock.acquire()
    except filelock.FileLockException:
        print("Could not acquire file lock (timeout=10s).")
        print("You can forcefully clear the lock with: daedalus clean-file-lock")
        print("Do not abuse this command as it may brick other currently running sessions on this machine!")
        exit(2)

    atexit.register(exit_handler)


def clean_running_session():
    global flock
    flock = filelock.FileLock("daedalus", session_uid=session_uid, timeout=10)
    flock.release(force=True)

start_session()

if len(sys.argv) == 2:
    if sys.argv[1] in ["clean-file-lock", "del-file-lock", "delete-file-lock", "clean-flock", "del-flock",
                       "delete-flock"]:
        clean_running_session()
        exit(0)

single_session()


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
        install_daedalus()

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
    plugins.autossh.AutoSSHManager.load_current_context()
    metadata = {
        "daedalus": None,
        "autossh": plugins.autossh.AutoSSHManager.get_metadata(),
        "hosts": plugins.hosts.HostsManager.get_metadata(),
        "sshconfig": plugins.sshconfig.SSHConfigManager.get_metadata(),
        "ssh": plugins.ssh.SSHManager.get_metadata()
    }
    if engine:
        metadata["daedalus"] = engine.get_metadata()
    return metadata


def print_help():
    print_help_line(0, "Daedalus is a collection of tools and scripts with the purpose of making deploying and " +
                    "sysadmin jobs easier while still having control and power of bash!")
    print("")
    print_help_line(1, "Generic commands:")
    print_help_line(2, "help", "print this description")
    print_help_line(2, "{clean-file-lock, del-file-lock, delete-file-lock, clean-flock, del-flock, delete-flock}",
                    "remove the current file lock. Use only in case of emergency")
    print_help_line(2, "upgrade", "update Daedalus to the latest version (may broke backwards compatibility)")
    print_help_line(2, "{deploy, deploy-to, install-on, setup-machine} <host_address>",
                    "install Daedalus on a remote machine")
    print_help_line(2, "get-metadata", "print to stdout a JSON containing various metadata from all plugins")
    print_help_line(2, "project", "submodule: add, remove and manage Daedalus projects")
    print_help_line(2, "startup", "trigger what happens at system booting")
    print_help_line(2, "shutdown", "trigger what happens att system shutdown")
    print("")
    print_help_line(1, "Project commands (requires an active working project):")
    print_help_line(2, "{cfs, configfs}", "submodule: access Daedalus' config file system for current project")
    print_help_line(2, "list-modules", "print all defined modules for current project")
    print_help_line(2, "list-installed-modules", "print all installed modules for current project")
    print_help_line(2, "info", "print a nice table about current project defined and installed modules")
    print_help_line(2, "update", "bulk update command")
    print_help_line(2, "update-version", "bulk update with reinstall forced (or purge and install)")
    print_help_line(2, "start", "bulk start installed modules")
    print_help_line(2, "stop", "bulk stop installed modules")
    print_help_line(2, "sync-stop", "bulk sync-stop installed modules")
    print_help_line(2, "restart", "bulk restart installed modules")
    print_help_line(2, "force-restart", "bulk force-restart installed modules")
    print_help_line(2, "info <module>", "prints information about module (if it is defined)")
    print_help_line(2, "list-dependencies <module>", "prints a list of dependencies for module")
    print_help_line(2, "{install, purge, reinstall, update, start, stop, restart, startup} <module>",
                    "executes one of these commands on module")
    print_help_line(2, "run <command> [arg1, arg2, ...]",
                    "runs a script/command in Daedalus environment (passing arguments after the command)")
    print_help_line(2, "exec <module> <command> [arg1, arg2, ...]",
                    "executes module-defined command (passing arguments after the command)")
    print("")
    print_help_line(1, "Plugins (run <plugin> help for details):")
    print_help_line(2, "hosts", "easy way to edit and apply changes to /etc/hosts file")
    print_help_line(2, "autossh", "manager for autossh connections")
    print_help_line(2, "https", "wrapper over letsencrypt SSL certificate creation and renewal")
    print_help_line(2, "ssh", "wrapper over ssh")
    print_help_line(2, "nginx", "manager for nginx configuration. Implements nginx-modules")
    print_help_line(2, "{sshconfig, sshconf}", "easy way to edit and apply changes to ssh config files")
    print_help_line(2, "apply", "collection for various system-wide parameter tweaking setup")
    print_help_line(2, "{template, jinja2}", "easy environment for jinja2 template files rendering")

valid_command = False
if len(sys.argv) == 1:
    print("Daedalus is here! (" + str(DAEDALUS_VERSION) + ")")
    valid_command = True
elif len(sys.argv) == 2:
    if sys.argv[1] == "help":
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
    if sys.argv[1] == "get-metadata":
        valid_command = True
        print(json.dumps(get_metadata()))
    elif sys.argv[1] == "startup":
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
