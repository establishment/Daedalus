import subprocess
import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(1, parent_dir)

from util import print_help_line


def print_help():
    print_help_line(0, "Daedalus \"https\" plugin help:")
    print_help_line(1, "help", "prints this description")
    print_help_line(1, "renew", "update all domains with new SSL keys/certificates")
    print_help_line(1, "test <domain>", "run a HTTPS lightweight server for quickly testing certificates for the " +
                    "specified domain")
    print_help_line(1, "new-ssl <domain> <email>", "generate SSL certificates for the specified domain setting " +
                    "<email> as the owner")


def parse_command(args):
    valid_command = False
    if len(args) == 1:
        valid_command = True
        print_help()
    elif len(args) == 2:
        if args[1] == "help":
            valid_command = True
            print_help()
        elif args[1] == "renew":
            valid_command = True
            renew_ssl()
    elif len(args) == 3:
        if args[1] == "test":
            valid_command = True
            run_test_server(args[2])
    elif len(args) == 4:
        if args[1] == "new-ssl":
            valid_command = True
            make_ssl_cert(args[2], args[3])
    return valid_command


def renew_ssl():
    subprocess.call("letsencrypt renew --standalone --standalone-supported-challenges http-01 --http-01-port 9999",
                    shell=True)


def run_test_server(domain):
    priv_path = "/etc/letsencrypt/live/" + domain + "/privkey.pem"
    cert_path = "/etc/letsencrypt/live/" + domain + "/cert.pem"
    source = "daedalus/tools/https-test-server"
    subprocess.call("node " + source + " " + priv_path + " " + cert_path + " " + domain, shell=True)


def make_ssl_cert(domain, email):
    subprocess.call("expect -c 'spawn letsencrypt certonly -a standalone -d " + domain + "; expect email; send \"" +
                    email + "\"; send \"\t\n\"; expect \"Please read\"; send \"\n\"; interact'", shell=True)

