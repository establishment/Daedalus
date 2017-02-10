import sys
import os
import subprocess
import tempfile

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import load_json, save_json, ensure_password, id_generator, run


def print_help():
    print("Daedalus \"ssh\" plugin help:")
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
    elif len(args) == 3:
        if args[1] in ["keyadd", "addkey", "add"]:
            valid_command = True
            SSHManager.ssh_addkey(args[2])
        elif args[1] in ["keyscan", "scan"]:
            valid_command = True
            SSHManager.ssh_keyscan(args[2])
        elif args[1] in ["keygen", "gen"]:
            valid_command = True
            SSHManager.ssh_keygen(args[2])
    elif len(args) == 4:
        if args[1] == "link":
            valid_command = True
            SSHManager.ssh_copy_id("id_rsa", args[2], args[3])
        elif args[1] == "deploy-to":
            valid_command = True
            SSHManager.ssh_deploy("root", args[2], args[3])
        elif args[1] in ["keygen", "gen"]:
            valid_command = True
            SSHManager.ssh_keygen(args[2], label=args[3])
        elif args[1] == "run":
            valid_command = True
            SSHManager.ssh_run("root", args[2], args[3])
        elif args[1] == "scp":
            valid_command = True
            SSHManager.scp(args[2], args[3])
    elif len(args) == 5:
        if args[1] == "link":
            valid_command = True
            SSHManager.ssh_copy_id(args[4], args[2], args[3])
        elif args[1] == "deploy-to":
            valid_command = True
            SSHManager.ssh_deploy(args[2], args[3], args[4])
        elif args[1] == "run":
            valid_command = True
            SSHManager.ssh_run(args[2], args[3], args[4])
    elif len(args) == 6:
        if args[1] == "link":
            valid_command = True
            SSHManager.ssh_copy_id(args[4], args[2], args[3], password=args[5])
    return valid_command


class SSHManager:
    default_path = None

    def __init__(self):
        self.entries = []

    def load(self, path=None):
        if not path:
            path = SSHManager.default_path
        data = load_json(path)
        if "entries" in data:
            self.entries = data["entries"]
        else:
            self.entries = []

    def save(self, path=None):
        if not path:
            path = SSHManager.default_path
        data = {
            "entries": self.entries
        }
        save_json(path, data)

    @classmethod
    def ssh_keyscan(cls, host):
        run("ssh-keyscan -t rsa " + host + " > ~/.ssh/known_hosts")

    @classmethod
    def ssh_addkey(cls, name):
        run(os.environ.get("DAEDALUS_ROOT") + "/tools/bash/add_ssh.sh " + name)

    @classmethod
    def ssh_keygen(cls, name, label=""):
        run(os.environ.get("DAEDALUS_ROOT") + "/tools/bash/generate_ssh.sh " + name + " " + label)

    @classmethod
    def autossh(cls, mapped_port, mapped_address, remote_port, remote_user, remote_host):
        command = "autossh -f -N -L " + mapped_port + ":" + mapped_address + ":" + remote_port
        command += " " + remote_user + "@" + remote_host
        subprocess.call(command, shell=True)

    @classmethod
    def ssh_copy_id(cls, key, user, hostname, password=None):
        if not cls.is_password_required(user, hostname):
            print("You are already ssh-linked with " + user + "@" + hostname)
            return
        if not password:
            password = ensure_password("Please enter password for " + user + "@" + hostname +
                                       " in order to copy ssh key.")
        command = "ssh-keygen -f \"/root/.ssh/known_hosts\" -R " + hostname
        subprocess.call(command, shell=True)
        new_file, path = tempfile.mkstemp()
        os.close(new_file)
        with open(path, 'w') as file:
            file.write(password)
        command = "sshpass -f " + path + " ssh-copy-id -i /root/.ssh/" + key + ".pub " + user + "@" + hostname
        subprocess.call(command, shell=True)
        os.remove(path)

    @classmethod
    def ssh_deploy(cls, user, hostname, script, password=None, force_key=False, auto=True):
        if force_key:
            cls.ssh_deploy_key(user, hostname, script)
        elif auto:
            cls.ssh_deploy_auto(user, hostname, script, password=password)
        else:
            cls.ssh_deploy_pw(user, hostname, script, password=password)

    @classmethod
    def ssh_deploy_auto(cls, user, hostname, script, password):
        if cls.is_password_required(user, hostname):
            cls.ssh_deploy_pw(user, hostname, script, password=password)
        else:
            cls.ssh_deploy_key(user, hostname, script)

    @classmethod
    def ssh_deploy_key(cls, user, hostname, script):
        host_script = "daedalus-deploy-script-" + id_generator() + ".sh"
        command = "scp " + script + " " + user + "@" + hostname + ":~/" + host_script
        subprocess.call(command, shell=True)
        command = "ssh -t " + user + "@" + hostname + " bash ~/" + host_script
        subprocess.call(command, shell=True)
        command = "ssh -t " + user + "@" + hostname + " rm ~/" + host_script
        subprocess.call(command, shell=True)

    @classmethod
    def ssh_deploy_pw(cls, user, hostname, script, password=None):
        if not password:
            password = ensure_password("Please enter password for " + user + "@" + hostname +
                                       " in order to deploy script!")
        new_file, path = tempfile.mkstemp()
        os.close(new_file)
        with open(path, 'w') as file:
            file.write(password)
        host_script = "daedalus-deploy-script-" + id_generator() + ".sh"
        command = "sshpass -f " + path + " scp " + script + " " + user + "@" + hostname + ":~/" + host_script
        subprocess.call(command, shell=True)
        command = "sshpass -f " + path + " ssh -t " + user + "@" + hostname + " bash ~/" + host_script
        subprocess.call(command, shell=True)
        command = "sshpass -f " + path + " ssh -t " + user + "@" + hostname + " rm ~/" + host_script
        subprocess.call(command, shell=True)

    @classmethod
    def ssh_run(cls, user, hostname, script, password=None, force_key=False, auto=True):
        if force_key:
            cls.ssh_run_key(user, hostname, script)
        elif auto:
            cls.ssh_run_auto(user, hostname, script, password=password)
        else:
            cls.ssh_run_pw(user, hostname, script, password=password)

    @classmethod
    def ssh_run_auto(cls, user, hostname, script, password=None):
        if cls.is_password_required(user, hostname):
            cls.ssh_run_pw(user, hostname, script, password=password)
        else:
            cls.ssh_run_key(user, hostname, script)

    @classmethod
    def ssh_run_key(cls, user, hostname, command):
        command = "ssh -t " + user + "@" + hostname + " \"" + command + "\""
        subprocess.call(command, shell=True)

    @classmethod
    def ssh_run_pw(cls, user, hostname, command, password=None):
        if not password:
            password = ensure_password("Please enter password for " + user + "@" + hostname +
                                       " in order to deploy script!")
        new_file, path = tempfile.mkstemp()
        os.close(new_file)
        with open(path, "w") as file:
            file.write(password)
        command = "sshpass -f " + path + " ssh -t " + user + "@" + hostname + " \"" + command + "\""
        subprocess.call(command, shell=True)

    @classmethod
    def scp(cls, path_from, path_to, password=None, force_key=False, auto=True):
        if force_key:
            cls.scp_key(path_from, path_to)
        elif auto:
            cls.scp_auto(path_from, path_to, password=password)
        else:
            cls.scp_pw(path_from, path_to, password=password)

    @classmethod
    def path_get_remote(cls, path):
        if "@" not in path:
            return None, None
        tokens = path.split("@")
        user = tokens[0]
        if ":" not in tokens[1]:
            return None, None
        hostname = tokens[1].split(":")[0]
        return user, hostname

    @classmethod
    def scp_get_remote(cls, path_from, path_to):
        user, hostname = cls.path_get_remote(path_from)
        if user:
            return user, hostname
        return cls.path_get_remote(path_to)

    @classmethod
    def scp_auto(cls, path_from, path_to, password=None):
        user, hostname = cls.scp_get_remote(path_from, path_to)
        if not user:
            print("SSH Manager: There is no path from or to any remote!")
            exit(2)
        if cls.is_password_required(user, hostname):
            cls.scp_pw(path_from, path_to, password=password)
        else:
            cls.scp_key(path_from, path_to)

    @classmethod
    def scp_key(cls, path_from, path_to):
        command = "scp " + path_from + " " + path_to
        subprocess.call(command, shell=True)

    @classmethod
    def scp_pw(cls, path_from, path_to, password=None):
        if not password:
            user, hostname = cls.scp_get_remote(path_from, path_to)
            if not user:
                print("SSH Manager: There is no path from or to any remote!")
                exit(2)
            password = ensure_password("Please enter password " + user + "@" + hostname + " in order to copy file!")
        new_file, path = tempfile.mkstemp()
        os.close(new_file)
        with open(path, "w") as file:
            file.write(password)
        command = "sshpass -f " + path + " scp " + path_from + " " + path_to
        subprocess.call(command, shell=True)

    @classmethod
    def is_password_required(cls, user, hostname):
        devnull = open(os.devnull, "w")
        result = subprocess.call("ssh " + user + "@" + hostname + " -qo PasswordAuthentication=no exit 0 || exit 1",
                                 shell=True, stdout=devnull, stderr=devnull)
        return result == 1
