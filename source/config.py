import os
import subprocess

from util import load_json, save_json


def project_print_help():
    print("Daedalus project manager help:")
    print("\t\tNothing for now!")


def project_parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print(Manager.projects["current"])
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            project_print_help()
        elif args[1] == "list":
            valid_command = True
            if not Manager.projects["projects"]:
                print("Config: There are no configured projects!")
            else:
                for project in Manager.projects["projects"]:
                    print(project)
        elif args[1] == "current":
            valid_command = True
            print(Manager.projects["current"])
        elif args[1] in ["root", "path"]:
            valid_command = True
            print(Manager.get_current_run_path())
    elif len(args) == 3:
        if args[1] in ["switch", "sw"]:
            valid_command = True
            Manager.set_project(args[2])
            Manager.save()
        elif args[1] in ["root", "path"]:
            valid_command = True
            print(Manager.get_run_path(args[2]))
        elif args[1] == "add":
            valid_command = True
            Manager.add(args[2], os.environ["DAEDALUS_WORKING_DIRECTORY"])
            Manager.save()
        elif args[1] in ["delete", "remove"]:
            valid_command = True
            Manager.delete(args[2])
            Manager.save()
    elif len(args) == 4:
        if args[1] == "add":
            valid_command = True
            Manager.add(args[2], args[3])
            Manager.save()
    return valid_command


class Manager:
    root_path = ""
    projects = {
        "current": None,
        "projects": {

        }
    }

    @classmethod
    def set_root(cls, root_path):
        cls.root_path = root_path

    @classmethod
    def load(cls):
        if not os.path.isfile(cls.root_path + "/state/projects.json"):
            return
        cls.projects = load_json(cls.root_path + "/state/projects.json")

    @classmethod
    def save(cls):
        os.makedirs(cls.root_path + "/state", exist_ok=True)
        save_json(cls.root_path + "/state/projects.json", cls.projects)

    @classmethod
    def is_in_project(cls):
        return cls.projects["current"] is not None

    @classmethod
    def get_project(cls):
        return cls.projects["current"]

    @classmethod
    def get_current_run_path(cls):
        if cls.projects["current"] is None:
            return cls.root_path
        if cls.projects["current"] not in cls.projects["projects"]:
            return cls.root_path
        return cls.projects["projects"][cls.get_project()]["root"]

    @classmethod
    def get_current_state_path(cls):
        if cls.projects["current"] is None:
            return

    @classmethod
    def ensure_project_exists(cls, project):
        if project not in cls.projects["projects"]:
            print("Config: Invalid project named \"" + project + "\"")
            exit(2)

    @classmethod
    def get_run_path(cls, project):
        cls.ensure_project_exists(project)
        return cls.projects["projects"][project]["root"]

    @classmethod
    def set_project(cls, project):
        cls.ensure_project_exists(project)
        cls.projects["current"] = project

    @classmethod
    def add(cls, project, path):
        if project == cls.projects["current"]:
            print("Config: project named \"" + project + "\" already exists at: " + path)
            exit(2)
        if not os.path.isdir(path + "/.daedalus"):
            print("Config: there is no .daedalus config folder at: " + path)
            exit(2)
        cls.projects["projects"][project] = {
            "root": path
        }

    @classmethod
    def delete(cls, project):
        cls.ensure_project_exists(project)
        del cls.projects["projects"][project]
        subprocess.call("rm -rf " + os.path.join(cls.root_path, "state/projects/" + project), shell=True)
        cls.projects["current"] = None

    @classmethod
    def get_env(cls, project=None):
        if project is None:
            project = cls.projects["current"]
        cls.ensure_project_exists(project)
        project_root = cls.get_run_path(project)

        env = {
            "DAEDALUS_PROJECT": project,
            "DAEDALUS_PROJECT_PATH": project_root,
            "DAEDALUS_CONFIG_PATH": os.path.join(project_root, ".daedalus"),
            "DAEDALUS_CONFIG_MODULES_PATH": os.path.join(project_root, ".daedalus/modules"),
            "DAEDALUS_STATE_PATH": os.path.join(cls.root_path, "state/projects/" + project),
            "DAEDALUS_STATE_MODULES_PATH": os.path.join(cls.root_path, "state/projects/" + project + "/modules")
        }
        return env

    @classmethod
    def get_state_path(cls, project=None):
        if project is None:
            return os.path.join(cls.root_path, "config")
        cls.ensure_project_exists(project)
        return os.path.join(cls.root_path, "state/projects/" + project)

    @classmethod
    def get_current_state_path(cls):
        return cls.get_state_path(cls.get_project())
