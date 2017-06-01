import os

from util import load_json, save_json, dict_merge


class JSONInclude:
    cache = {}

    @classmethod
    def get(cls, path):
        return JSONInclude(path)

    def __init__(self, path):
        path_to_dir = os.path.dirname(path)
        self.path = path
        self.data = load_json(path)
        if "include" in self.data:
            if type(self.data["include"]) is str:
                dependencies = [self.data["include"]]
            elif type(self.data["include"]) is list:
                dependencies = self.data["include"]
            else:
                dependencies = []
            for dependency in dependencies:
                if not dependency.startswith("/"):
                    dependency_full_path = os.path.join(path_to_dir, dependency)
                else:
                    dependency_full_path = dependency
                self.update(JSONInclude.get(dependency_full_path))
        if "include" in self.data:
            del self.data["include"]

    def update(self, other, overwrite=False, merge_lists=True):
        dict_merge(self.data, other.data, overwrite=overwrite, merge_lists=merge_lists)

    def save(self, path):
        save_json(path, self.data)
