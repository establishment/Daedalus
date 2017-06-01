import subprocess
import json
import os
import getpass
import sys
import string
import random
import collections


def renew_env_var(key, value):
    # Take care, as this function will not change environment variables for parents (aka. bash).
    # In order for the terminal to recognize the new environment you need to restart your current session.
    key = str(key)
    value = str(value)
    run("sed -i '/export " + key + "=.*/d' /etc/profile > /dev/null 2>&1", shell=True)
    run("sed -i '/export " + key + "=.*/d' /etc/bash.bashrc > /dev/null 2>&1", shell=True)
    run("sed -i '/export " + key + "=.*/d' ~/.bash_profile > /dev/null 2>&1", shell=True)
    run("sed -i '/export " + key + "=.*/d' ~/.bash_login > /dev/null 2>&1", shell=True)
    run("sed -i '/export " + key + "=.*/d' ~/.profile > /dev/null 2>&1", shell=True)
    os.putenv(key, value)
    os.environ[key] = value
    run("echo \"export " + key + "=" + value + "\" >> /etc/profile", shell=True)
    run("echo \"export " + key + "=" + value + "\" >> /etc/bash.bashrc", shell=True)
    run("echo \"export " + key + "=" + value + "\" >> ~/.bash_profile", shell=True)
    run("echo \"export " + key + "=" + value + "\" >> ~/.bash_login", shell=True)
    run("echo \"export " + key + "=" + value + "\" >> ~/.profile", shell=True)


def apt_update():
    return run("apt-get update", shell=True)


def apt_get(app_name):
    if isinstance(app_name, list):
        for name in app_name:
            apt_get(name)
    else:
        run("apt-get install -y " + app_name, shell=True)


def load_json(path):
    try:
        with open(path) as data_file:
            return json.load(data_file)
    except json.decoder.JSONDecodeError as e:
        print("Error: invalid JSON format at \"" + path + "\"")
    return {}


def save_json(path, data):
    with open(path, 'w') as data_file:
        json.dump(data, data_file)


def get_dirs_in(path):
    try:
        return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    except:
        return []


def get_files_in(path):
    try:
        return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    except:
        return []


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
    return "".join(random.choice(chars) for _ in range(size))


def sanitize_env(env):
    for key in env:
        if env[key] is None:
            env[key] = ""
    return env


def run(command, env=None, overwrite_env=False, shell=True):
    global current_process
    if overwrite_env:
        updated_env = env
    else:
        updated_env = os.environ.copy()
        if env:
            updated_env.update(env)
    updated_env = sanitize_env(updated_env)
    current_process = subprocess.Popen(command, env=updated_env, shell=shell)
    current_process.wait()
    rc = current_process.returncode
    current_process = None
    return rc


def get_real_path(path, work_dir=None):
    if path.startswith("/"):
        return path
    if work_dir is None:
        work_dir = os.environ.get("DAEDALUS_WORKING_DIRECTORY")
    return os.path.join(work_dir, path)


def print_help_line(nest_level, col1, col2=None, col1_size=30, col_separator=" - "):
    if col2 is not None:
        col2 = col_separator + col2
    else:
        col2 = ""
    print(get_spaces(nest_level * 2) + col1 + get_spaces(col1_size - len(col1)) + col2)


def escape_arg(arg, add_quotes=True):
    temp_arg = ""
    for c in arg:
        if c == "\"":
            temp_arg += "\\"
        temp_arg += c
    if add_quotes:
        return "\"" + temp_arg + "\""
    else:
        return temp_arg


def dict_merge(dct, merge_dct, overwrite=False, merge_lists=True):
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            dict_merge(dct[k], merge_dct[k])
        elif (k in dct and isinstance(dct[k], list)
              and isinstance(merge_dct[k], list)):
            if overwrite:
                dct[k] = merge_dct[k]
            elif merge_lists:
                dct[k] = merge_dct[k] + dct[k]
        elif k in dct:
            if overwrite:
                dct[k] = merge_dct[k]
        else:
            dct[k] = merge_dct[k]
