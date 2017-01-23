import subprocess
import json
import os
import getpass
import sys
import string
import random


def renew_env_var(key, value):
    # Take care, as this function will not change environment variables for parents (aka. bash).
    # In order for the terminal to recognize the new environment you need to restart bash.
    key = str(key)
    value = str(value)
    subprocess.call("sed -i '/export " + key + "=.*/d' /etc/profile > /dev/null 2>&1", shell=True)
    subprocess.call("sed -i '/export " + key + "=.*/d' /etc/bash.bashrc > /dev/null 2>&1", shell=True)
    subprocess.call("sed -i '/export " + key + "=.*/d' ~/.bash_profile > /dev/null 2>&1", shell=True)
    subprocess.call("sed -i '/export " + key + "=.*/d' ~/.bash_login > /dev/null 2>&1", shell=True)
    subprocess.call("sed -i '/export " + key + "=.*/d' ~/.profile > /dev/null 2>&1", shell=True)
    os.putenv(key, value)
    os.environ[key] = value
    subprocess.call("echo \"export " + key + "=" + value + "\" >> /etc/profile", shell=True)
    subprocess.call("echo \"export " + key + "=" + value + "\" >> /etc/bash.bashrc", shell=True)
    subprocess.call("echo \"export " + key + "=" + value + "\" >> ~/.bash_profile", shell=True)
    subprocess.call("echo \"export " + key + "=" + value + "\" >> ~/.bash_login", shell=True)
    subprocess.call("echo \"export " + key + "=" + value + "\" >> ~/.profile", shell=True)


def apt_update():
    return subprocess.call("apt-get update", shell=True)


def apt_get(app_name):
    if isinstance(app_name, list):
        for name in app_name:
            apt_get(name)
    else:
        subprocess.call("apt-get install -y " + app_name, shell=True)


def load_json(path):
    with open(path) as data_file:
        return json.load(data_file)


def save_json(path, data):
    with open(path, 'w') as data_file:
        json.dump(data, data_file)


def get_dirs_in(path):
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]


def get_files_in(path):
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]


def repeat_str(st, count):
    ans = ""
    for i in range(count):
        ans += st
    return ans


def get_spaces(count):
    return repeat_str(" ", count)


def format_two_column(col1, col2, total_length):
    return col1 + get_spaces(total_length - len(col1) - len(col2)) + col2


def ensure_file_exists(path):
    if not os.path.isfile(path):
        open(path, 'w+')


def ensure_json_exists(path):
    make_json = False
    if not os.path.isfile(path):
        make_json = True
    else:
        try:
            load_json(path)
        except Exception as e:
            make_json = True
    if make_json:
        with open(path, "w") as file:
            file.write("{}")


def get_password(verify=True):
    sys.stdout.flush()
    password = getpass.getpass()
    if not verify:
        return password

    password_verify = getpass.getpass(prompt="Verify password: ")
    if password != password_verify:
        return None
    return password


def ensure_password(text):
    print(text)
    password = None
    while not password:
        password = get_password()
        if not password:
            print("Passwords does not match!")
    return password


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def run(command, env=None, overwrite_env=False, shell=True):
    if overwrite_env:
        updated_env = env
    else:
        updated_env = os.environ.copy()
        if env:
            updated_env.update(env)

    child = subprocess.Popen(command, env=updated_env, shell=shell)
    child.wait()
    return child.returncode

def get_real_path(path):
    if path.startswith("/"):
        return path
    return os.environ.get("DAEDALUS_WORKING_DIRECTORY") + "/" + path
