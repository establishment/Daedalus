import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import get_files_in, format_two_column, print_help_line


def print_help():
    print_help_line(0, "Daedalus \"Nginx\" plugin help:")
    print_help_line(1, "help", "prints this description")
    print_help_line(1, "list", "prints currently enabled sites and if it supports or not Daedalus' nginx-modules")
    print_help_line(1, "{list-extensions, list-ext} <domain>", "prints installed extensions for the specified domain")
    print_help_line(1, "{link, link-ext, link-extension, link-ext-to, link-extension-to} <domain> <extension>",
                    "installs (link) domain with the specified extension")
    print_help_line(1, "{unlink, unlink-ext, unlink-extension, unlink-ext-from, unlink-extension-from} <domain> " +
                    "<extension>", "uninstalls (unlink) domain from the specified extension")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
        elif args[1] == "list":
            valid_command = True
            nginx_engine = NginxEngine()
            print("Current active domains:")
            print(format_two_column("Domain", "Support extensions", 80))
            for domain in nginx_engine.domains:
                print(format_two_column(domain, str(nginx_engine.domains[domain]["extension"]), 80))
    elif len(args) == 3:
        if args[1] in ["list-extensions", "list-ext"]:
            valid_command = True
            nginx_engine = NginxEngine()
            if args[2] not in nginx_engine.domains:
                print("NginxEngine: domain \"" + args[2] + "\" does not exists!")
                exit(2)
            if not nginx_engine.domains[args[2]]["extension"]:
                print("NginxEngine: domain \"" + args[2] + "\" does not support extensions!")
                exit(2)
            if len(nginx_engine.domains[args[2]]["installed_extensions"]) == 0:
                print("NginxEngine: domain \"" + args[2] + "\" does not have any extension installed!")
                exit(2)
            print(format_two_column("Extension", "Enabled", 80))
            for extension in nginx_engine.domains[args[2]]["installed_extensions"]:
                is_enabled = extension in nginx_engine.domains[args[2]]["enabled_extensions"]
                print(format_two_column(extension, str(is_enabled), 80))
    elif len(args) == 4:
        if args[1] in ["link", "link-ext", "link-extension", "link-ext-to", "link-extension-to"]:
            valid_command = True
            nginx_engine = NginxEngine()
            nginx_engine.link(args[2], args[3])
            nginx_engine.update()
        if args[1] in ["unlink", "unlink-ext", "unlink-extension", "unlink-ext-from", "unlink-extension-from"]:
            valid_command = True
            nginx_engine = NginxEngine()
            nginx_engine.unlink(args[2], args[3])
            nginx_engine.update()
    return valid_command


class NginxEngine:
    DEFAULT_DOMAINS_PATH = "/etc/nginx/sites-enabled"
    DEFAULT_EXTENSIONS_PATH = "/etc/nginx/sites-extensions"

    def __init__(self):
        self.domains = {}
        self.load()

    @classmethod
    def parse_nginx_line(self, line):
        if "include " not in line:
            return None
        tokens = line.split("include ")
        path = tokens[len(tokens) - 1]
        if ";" not in path:
            return None
        tokens = path.split(";")
        path = tokens[0]
        tokens = path.split("/")
        file = tokens[len(tokens) - 1]
        if "-extension-" not in file:
            return None
        tokens = file.split("-extension-")
        if len(tokens) != 2:
            return None
        return tokens[1]

    @classmethod
    def load_extension_file(self, extension_path):
        with open(extension_path, "r") as file:
            data = file.read()
            lines = data.splitlines()
            extensions = []
            for line in lines:
                extension = NginxEngine.parse_nginx_line(line)
                if extension is not None:
                    extensions.append(extension)
            return extensions

    def update_extension_file(self, extensions_path, domain):
        with open(os.path.join(extensions_path, domain + "-extension"), "w") as file:
            for extension in self.domains[domain]["enabled_extensions"]:
                file.write("include ")
                file.write(os.path.join(extensions_path, domain + "-extension-" + extension))
                file.write(";\n")

    def update(self, extensions_path=DEFAULT_EXTENSIONS_PATH):
        for domain in self.domains:
            if self.domains[domain]["extension"]:
                self.update_extension_file(extensions_path, domain)

    def load(self, domains_path=DEFAULT_DOMAINS_PATH, extensions_path=DEFAULT_EXTENSIONS_PATH):
        domains = get_files_in(domains_path)
        if "default" in domains:
            domains.remove("default")

        for domain in domains:
            self.domains[domain] = {
                "extension": False,
                "installed_extensions": [],
                "enabled_extensions": []
            }

        all_installed_extensions = []
        os.makedirs(extensions_path, exist_ok=True)
        extensions = get_files_in(extensions_path)
        for extension in extensions:
            if extension.endswith("-extension"):
                domain = extension[:-len("-extension")]
                if domain not in self.domains:
                    print("NginxEngine: extension \"" + extension + "\" left for unavailable domain \"" + domain + "\".")
                    exit(2)
                self.domains[domain]["extension"] = True
                extension_path = os.path.join(extensions_path, extension)
                self.domains[domain]["enabled_extensions"] = NginxEngine.load_extension_file(extension_path)
            else:
                all_installed_extensions.append(extension)

        for extension in all_installed_extensions:
            tokens = extension.split("-")
            if len(tokens) != 3:
                print("NginxEngine: invalid extension name: " + extension)
                print("NginxEngine: going to skip ... ")
                continue
            domain = tokens[0]
            extension_name = tokens[2]
            self.domains[domain]["installed_extensions"].append(extension_name)

    def link(self, domain, extension):
        if domain not in self.domains:
            print("NginxEngine: domain \"" + domain + "\" does not exists!")
            exit(2)
        if extension in self.domains[domain]["enabled_extensions"]:
            print("NginxEngine: domain \"" + domain + "\" already use extension \"" + extension + "\"")
            exit(2)
        self.domains[domain]["enabled_extensions"].append(extension)

    def unlink(self, domain, extension):
        if domain not in self.domains:
            print("NginxEngine: domain \"" + domain + "\" does not exists!")
            exit(2)
        if extension not in self.domains[domain]["enabled_extensions"]:
            print("NginxEngine: domain \"" + domain + "\" is not using extension \"" + extension + "\"")
            exit(2)
        self.domains[domain]["enabled_extensions"].remove(extension)
