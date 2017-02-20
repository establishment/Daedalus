import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import print_help_line


def print_help():
    print_help_line(0, "Daedalus \"hosts\" plugin help:")
    print_help_line(1, "help", "prints this description")
    print_help_line(1, "show", "prints the current hosts configuration")
    print_help_line(1, "show-alias <alias>", "prints the current configuration for the specified alias")
    print_help_line(1, "show-up <ip>", "prints the current configuration for the specified ip")
    print_help_line(1, "delete-alias <alias>", "delete the entry with the specified alias")
    print_help_line(1, "delete-ip <ip>", "delete all entries with the specified ip")
    print_help_line(1, "add <alias> <ip>", "add a new entry (or overwrite)")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
        elif args[1] == "show":
            valid_command = True
            hosts = HostsManager()
            hosts.load()
            print(hosts.ip_to_aliases)
    elif len(args) == 3:
        if args[1] == "show-alias":
            valid_command = True
            hosts = HostsManager()
            hosts.load()
            print(hosts.get_ip(args[2]))
        elif args[1] == "show-ip":
            valid_command = True
            hosts = HostsManager()
            hosts.load()
            print(hosts.get_aliases(args[2]))
        elif args[1] == "delete-alias":
            valid_command = True
            hosts = HostsManager()
            hosts.load()
            hosts.delete_alias(args[2])
            hosts.save()
        elif args[1] == "delete-ip":
            valid_command = True
            hosts = HostsManager()
            hosts.load()
            hosts.delete_ip(args[2])
            hosts.save()
    elif len(args) == 4:
        if args[1] == "add":
            valid_command = True
            hosts = HostsManager()
            hosts.load()
            hosts.add(args[2], args[3])
            hosts.save()
    return valid_command


class HostsManager:
    def __init__(self):
        self.alias_to_ip = {}
        self.ip_to_aliases = {}

    @classmethod
    def get_metadata(cls):
        hosts = HostsManager()
        hosts.load()
        data = {
            "alias_to_ip": hosts.alias_to_ip,
            "ip_to_aliases": hosts.ip_to_aliases
        }
        return data

    def load(self, path="/etc/hosts"):
        with open(path) as file:
            content = [line.strip('\n').strip() for line in file.readlines()]
            self.parse(content)

    def save(self, path="/etc/hosts"):
        with open(path, 'w') as file:
            for ip, aliases in self.ip_to_aliases.items():
                file.write(ip)
                for alias in aliases:
                    file.write("\t")
                    file.write(alias)
                file.write("\n")

    def parse(self, content):
        for line in content:
            if HostsManager.is_comment_line(line):
                continue
            tokens = line.split()
            if len(tokens) >= 2:
                ip = tokens[0]
                tokens.pop(0)
                for alias in tokens:
                    self.add(alias, ip)

    def delete_alias(self, alias):
        ip = None
        if alias in self.alias_to_ip:
            ip = self.alias_to_ip[alias]
            del self.alias_to_ip[alias]
        if ip:
            self.ip_to_aliases[ip] = [this_alias for this_alias in self.ip_to_aliases[ip] if this_alias != alias]
            if not self.ip_to_aliases[ip]:
                del self.ip_to_aliases[ip]

    def delete_ip(self, ip):
        aliases = self.get_aliases(ip)
        for alias in aliases:
            self.delete_alias(alias)

    def add(self, alias, ip):
        self.alias_to_ip[alias] = ip
        if ip not in self.ip_to_aliases:
            self.ip_to_aliases[ip] = [alias]
        else:
            self.ip_to_aliases[ip].append(alias)

    def get_ip(self, alias):
        if alias not in self.alias_to_ip:
            return None
        return self.alias_to_ip[alias]

    def get_aliases(self, ip):
        if ip not in self.ip_to_aliases:
            return None
        return self.ip_to_aliases[ip]

    @classmethod
    def is_comment_line(cls, line):
        if len(line) == 0:
            return True
        if line[0] == '#':
            return True
        return False
