import os
import json

from util import get_files_in


# implementation for single value ConfigFS
class ConfigFSValue:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    def get_all_keys(self):
        return get_files_in(self.root_dir)

    def get(self, key):
        if not self.exists(key):
            return None
        with open(self.get_path(key)) as file:
            return file.read()

    def set(self, key, value):
        self.delete(key)
        with open(self.get_path(key), "w+") as file:
            file.write(value)

    def delete(self, key):
        if self.exists(key):
            os.remove(self.get_path(key))

    def exists(self, key):
        return os.path.isfile(self.get_path(key))

    def get_path(self, key):
        return self.root_dir + "/" + key


# implementation for multiple value (lists) ConfigFS
class ConfigFSList:
    def __init__(self, root_dir):
        self.root_dir = root_dir + "/list"
        os.makedirs(self.root_dir, exist_ok=True)

    @classmethod
    def has_key_prefix(cls, key):
        return key.upper().startswith("LIST:")

    @classmethod
    def safe_key(cls, key):
        if cls.has_key_prefix(key):
            return key[5:]
        return key

    def get_all_keys(self):
        return get_files_in(self.root_dir)

    def get(self, key):
        key = ConfigFSList.safe_key(key)
        if not self.exists(key):
            return None
        with open(self.get_path(key), "r") as file:
            return json.load(file)

    def set(self, key, value):
        key = ConfigFSList.safe_key(key)
        if type(value) is not list:
            value = [value]
        self.delete(key)
        with open(self.get_path(key), "w") as file:
            json.dump(value, file)

    def remove(self, key, value):
        key = ConfigFSList.safe_key(key)
        content = self.get(key)
        if content is None:
            content = []
        content.remove(value)
        self.set(key, content)

    def insert(self, key, value):
        key = ConfigFSList.safe_key(key)
        content = self.get(key)
        if content is None:
            content = []
        if value not in content:
            content.append(value)
        self.set(key, content)

    def contains(self, key, value):
        key = ConfigFSList.safe_key(key)
        list_value = self.get(key)
        return value in list_value

    def delete(self, key):
        key = ConfigFSList.safe_key(key)
        if self.exists(key):
            os.remove(self.get_path(key))

    def exists(self, key):
        key = ConfigFSList.safe_key(key)
        return os.path.isfile(self.get_path(key))

    def get_path(self, key):
        key = ConfigFSList.safe_key(key)
        return self.root_dir + "/" + key


# wrapper for all types of ConfigFS components
class ConfigFS:
    def __init__(self, root_dir):
        self.value = ConfigFSValue(root_dir)
        self.list = ConfigFSList(root_dir)

    def get_all_keys(self):
        keys = self.value.get_all_keys()
        list_keys = self.list.get_all_keys()
        for list_key in list_keys:
            keys.append("list:" + list_key)
        return keys

    def get(self, key):
        if ConfigFSList.has_key_prefix(key):
            return self.list.get(key)
        return self.value.get(key)

    def set(self, key, value):
        if ConfigFSList.has_key_prefix(key):
            return self.list.set(key, value)
        return self.value.set(key, value)

    def delete(self, key):
        if ConfigFSList.has_key_prefix(key):
            return self.list.delete(key)
        return self.value.delete(key)

    def exists(self, key):
        if ConfigFSList.has_key_prefix(key):
            return self.list.exists(key)
        return self.value.exists(key)

    def get_path(self, key):
        if ConfigFSList.has_key_prefix(key):
            return self.list.get_path(key)
        return self.value.get_path(key)
