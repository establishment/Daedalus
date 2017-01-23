import re
import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import format_two_column, run


def print_help():
    print("Daedalus \"sshconfig\" plugin help:")
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
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.display()
    elif len(args) == 3:
        if args[1] == ["add-host", "insert-host"]:
            valid_command = True
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.add_host(args[2])
            sshconfig.save()
        elif args[1] in ["remove-host", "delete-host"]:
            valid_command = True
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.remove_host(args[2])
            sshconfig.save()
        elif args[1] in ["show", "display"]:
            valid_command = True
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.display_global(args[2])
        elif args[1] in ["show-host", "display-host"]:
            valid_command = True
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.display_host(args[2])
        elif args[1] in ["remove", "delete"]:
            valid_command = True
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.remove(args[2])
            sshconfig.save()
    elif len(args) == 4:
        if args[1] in ["remove-host-field", "delete-host-field"]:
            valid_command = True
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.remove_host_field(args[2], args[3])
            sshconfig.save()
        elif args[1] in ["show-host-field", "display-host-field"]:
            valid_command = True
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.display_host_field(args[2], args[3])
        elif args[1] in ["add", "insert"]:
            valid_command = True
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.add(args[2], args[3])
            sshconfig.save()
    elif len(args) == 5:
        if args[1] == ["add-host-field", "insert-host-field"]:
            valid_command = True
            sshconfig = SSHConfigManager()
            sshconfig.load()
            sshconfig.add_host_field(args[2], args[3], args[4])
            sshconfig.save()
    return valid_command


class SSHConfigManager:
    def __init__(self):
        self.hosts = {}
        self.global_config = {}

    @classmethod
    def global_config_have_equal(cls, name):
        return name in ["UserKnownHostsFile"]

    @classmethod
    def get_metadata(cls):
        sshconfig = SSHConfigManager()
        sshconfig.load()
        data = {
            "hosts": sshconfig.hosts,
            "global": sshconfig.global_config
        }
        return data

    def load(self, path="/root/.ssh/config"):
        if not os.path.isfile(path):
            self.hosts = {}
            self.global_config = {}
            return
        with open(path) as file:
            content = [line.strip('\n') for line in file.readlines()]
            self.parse(content)

    def save_global(self, file):
        for key in self.global_config:
            if SSHConfigManager.global_config_have_equal(key):
                file.write(key + "=" + self.global_config[key])
            else:
                file.write(key + " " + self.global_config[key])
            file.write("\n")
        file.write("\n")

    def save_host(self, file, host_name):
        file.write("Host " + host_name + "\n")
        for key in self.hosts[host_name]:
            file.write("    " + key + " " + self.hosts[host_name][key] + "\n")
        file.write("\n")

    def save(self, path="/root/.ssh/config"):
        with open(path, 'w') as file:
            self.save_global(file)
            for host_name in self.hosts:
                self.save_host(file, host_name)
        run("chmod 600 " + path)

    def ensure_host_exists(self, host):
        if host not in self.hosts:
            print("SSHConfigManager: host \"" + host + "\" does not exists!")
            exit(2)

    def ensure_host_field_exists(self, host, field):
        self.ensure_host_exists(host)
        if field not in self.hosts[host]:
            print("SSHConfigManager: host \"" + host + "\" does not contain field \"" + field + "\"!")
            exit(2)

    def ensure_global_field(self, field):
        if field not in self.global_config:
            print("SSHConfigManager: config does not contain field \"" + field + "\"!")
            exit(2)

    def add(self, field, value):
        self.global_config[field] = value

    def remove(self, field):
        self.ensure_global_field(field)
        del self.global_config[field]

    def add_host(self, host_name):
        if host_name in self.hosts:
            print("SSHConfigManager: host \"" + host_name + "\" already exists!")
            exit(2)
        self.hosts[host_name] = {}

    def remove_host(self, host_name):
        self.ensure_host_exists(host_name)
        del self.hosts[host_name]

    def add_host_field(self, host_name, field, value):
        self.ensure_host_exists(host_name)
        self.hosts[host_name][field] = value

    def remove_host_field(self, host_name, field):
        self.ensure_host_field_exists(host_name, field)
        del self.hosts[host_name][field]

    @classmethod
    def get_field_value(cls, line, separator=None):
        if not separator:
            tokens = line.split()
        else:
            tokens = line.split(separator)
        field = tokens[0]
        value = ""
        for index in range(1, len(tokens)):
            value += tokens[index]
            if index != len(tokens) - 1:
                value += " "
        return field, value

    def display(self):
        if not self.global_config:
            print("There is no global config fields!")
        else:
            print("Global config:")
            for field in self.global_config:
                print(format_two_column(field, str(self.global_config[field]), 80))
        print("")

        if not self.hosts:
            print("There are no hosts configured!")
        else:
            for host in self.hosts:
                print("Host: " + host)
                for key in self.hosts[host]:
                    print(format_two_column(key, str(self.hosts[host][key]), 80))
                print("")

    def display_host(self, host):
        self.ensure_host_exists(host)
        print("Host: " + host)
        if not self.hosts[host]:
            print("No fields registered for this host!")
        else:
            for key in self.hosts[host]:
                print(format_two_column(key, str(self.hosts[host][key]), 80))

    def display_global(self, field):
        self.ensure_global_field(field)
        print(field + ":\t\t" + self.global_config[field])

    def display_host_field(self, host, field):
        self.ensure_host_field_exists(host, field)
        print("Host: " + host + "\t\t" + field + ": " + self.hosts[host][field])

    def parse(self, content):
        self.global_config = {}
        self.hosts = {}
        prev_host = None
        for line in content:
            if line.strip() == "":
                continue
            if re.match(r'\s', line):
                if not prev_host:
                    continue
                field, value = SSHConfigManager.get_field_value(line.strip())
                self.hosts[prev_host][field] = value
            else:
                line = line.strip()
                if line.upper().startswith("HOST "):
                    tokens = line.split()
                    if len(tokens) != 2:
                        continue
                    prev_host = tokens[1]
                    self.hosts[prev_host] = {}
                else:
                    if "=" in line:
                        field, value = SSHConfigManager.get_field_value(line, "=")
                    else:
                        field, value = SSHConfigManager.get_field_value(line)
                    self.global_config[field] = value
