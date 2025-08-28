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
        # Build per-package OPackage skeletons
        output = {}
        for (_, cls) in self.cls_dict.items():
            pkg_name = cls.pkg
            if pkg_name not in output:
                output[pkg_name] = {
                    "name": pkg_name,
                    "version": None,
                    "disabled": False,
                    "metadata": {"tags": []},
                    "classes": [],
                    "functions": [],
                    "dependencies": [],
                    "deployments": [],
                }
            # Merge in any @package metadata stored on the class
            try:
                pkg_meta = getattr(getattr(cls, 'cls', None), '_oaas_package_meta', None)
                if pkg_meta:
                    if pkg_meta.get('version') is not None:
                        output[pkg_name]['version'] = pkg_meta['version']
                    # Merge metadata fields
                    md = output[pkg_name]['metadata']
                    src_md = pkg_meta.get('metadata', {})
                    if src_md.get('author'):
                        md['author'] = src_md['author']
                    if src_md.get('description'):
                        md['description'] = src_md['description']
                    if src_md.get('tags'):
                        # dedupe tags
                        md['tags'] = list({*md.get('tags', []), *src_md['tags']})
                    # Merge dependencies
                    if pkg_meta.get('dependencies'):
                        output[pkg_name]['dependencies'] = list({
                            *output[pkg_name]['dependencies'], *pkg_meta['dependencies']
                        })
            except Exception:
                pass
            cls.export_pkg(output[pkg_name])
        return output

    def print_pkg(self) -> str:
        out = ""
        for (_, pkg) in self.export_pkg().items():
            out += yaml.dump(pkg, indent=2)
            out += "---\n"
        return out

    def get_cls_meta(self, cls_id: str) -> ClsMeta:
        return self.cls_dict.get(cls_id)