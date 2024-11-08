from typing import Any

import yaml

from oaas_sdk2_py.model import ClsMeta


class MetadataRepo:
    cls_dict: dict[str, ClsMeta] = {}

    def add_cls(self, cls_meta: ClsMeta):
        self.cls_dict[cls_meta.pkg + '.' + cls_meta.name] = cls_meta

    def __str__(self):
        text = "{"
        for (k,v) in self.cls_dict.items():
            text += f"{k}: {v.__str__()},"
        text += "}"
        return text

    def export_pkg(self) -> dict[str, Any]:
        output = {}
        for (_, cls) in self.cls_dict.items():
            pkg_name = cls.pkg
            if pkg_name not in output:
                output[pkg_name] = {"name": pkg_name, "classes": [], "functions": []}
            cls.export_pkg(output[pkg_name])
        return output

    def print_pkg(self):
        for (_, pkg) in self.export_pkg().items():
            print(yaml.dump(pkg, indent=2))
            print("---")

    def get_cls_meta(self, cls_id: str) -> ClsMeta:
        return self.cls_dict[cls_id]