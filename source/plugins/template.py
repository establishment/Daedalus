import sys
import os
import jinja2

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

import config
from util import load_json, save_json, ensure_json_exists, format_two_column, get_real_path


def print_help():
    print("Daedalus \"template\" plugin help:")
    print("\t\tNothing for now!")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
        elif args[1] in ["show", "display"]:
            valid_command = True
            TemplateManager.load_current_context()
            template_manager = TemplateManager()
            template_manager.load()
            template_manager.display()
        elif args[1] in ["clear", "reset"]:
            valid_command = True
            TemplateManager.load_current_context()
            template_manager = TemplateManager()
            template_manager.load()
            template_manager.clear()
            template_manager.save()
    elif len(args) == 3:
        if args[1] in ["delete", "remove"]:
            valid_command = True
            TemplateManager.load_current_context()
            template_manager = TemplateManager()
            template_manager.load()
            template_manager.delete(args[2])
            template_manager.save()
        elif args[1] in ["show", "display"]:
            valid_command = True
            TemplateManager.load_current_context()
            template_manager = TemplateManager()
            template_manager.load()
            template_manager.display_key(args[2])
        elif args[1] in ["render"]:
            valid_command = True
            TemplateManager.load_current_context()
            template_manager = TemplateManager()
            template_manager.load()
            template_manager.render(get_real_path(args[2]), get_real_path(args[2]))
    elif len(args) == 4:
        if args[1] in ["set", "add"]:
            valid_command = True
            TemplateManager.load_current_context()
            template_manager = TemplateManager()
            template_manager.load()
            template_manager.set(args[2], args[3])
            template_manager.save()
        elif args[1] in ["render-to"]:
            valid_command = True
            TemplateManager.load_current_context()
            template_manager = TemplateManager()
            template_manager.load()
            template_manager.render(get_real_path(args[2]), get_real_path(args[3]))
    return valid_command


class TemplateManager:
    default_path = None

    def __init__(self):
        self.context = None

    @classmethod
    def load_current_context(cls):
        template_context_path = config.Manager.get_current_state_path() + "/template_context.json"
        ensure_json_exists(template_context_path)
        cls.set_default_path(template_context_path)

    def load(self, path=None):
        if not path:
            path = TemplateManager.default_path
        self.context = load_json(path)

    def save(self, path=None):
        if not path:
            path = TemplateManager.default_path
        if not self.context:
            self.context = {}
        save_json(path, self.context)

    def display(self):
        if not self.context:
            print("There is currently no context defined!")
        else:
            print("Current template context:")
            for key in self.context:
                print(format_two_column(key, self.context[key], 80))

    def ensure_key_exists(self, key):
        if key not in self.context:
            print("There is no value for key \"" + key + "\"!")
            exit(0)

    def display_key(self, key):
        self.ensure_key_exists(key)
        print(format_two_column(key, self.context[key], 80))

    def delete(self, key):
        self.ensure_key_exists(key)
        del self.context[key]

    def clear(self):
        self.context = {}

    def set(self, key, value):
        self.context[key] = value

    def render(self, path_from, path_to):
        with open(path_from, "r") as content_file:
            template_content = content_file.read()
        rendered_content = jinja2.Environment().from_string(template_content).render(self.context)
        with open(path_to, "w") as rendered_file:
            rendered_file.write(rendered_content)

    @classmethod
    def set_default_path(cls, path):
        cls.default_path = path

