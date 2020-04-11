from collections import defaultdict
from pathlib import Path


class Modules(dict):
    CFG_KEY = "modules_enabled"
    _cache = defaultdict(lambda: None)

    def __init__(self, cfg):
        self.cfg = cfg

    def _populate_cache(self):
        if not self._cache:
            # read and cache module info
            modules_path = Path("modules/")
            for module_path in [p for p in modules_path.iterdir() if p.is_dir()]:
                # e.g. modules/spark_cluster => spark_cluster
                module_info = {}
                module_name = module_path.name

                # read module infos from modules __init__.py
                exec(Path(module_path, "__init__.py").read_text(), module_info)
                self._cache[module_name] = {
                    k: module_info[k] for k in module_info.keys() & {"NAME", "DESCRIPTION", "WARNING"}
                }
                self._cache[module_name]["PATH"] = module_path.absolute()

                # read module env
                env = {"MODULE_ENV": {module_name: {}}}
                exec(Path(module_path, "env.py").read_text(), env["MODULE_ENV"][module_name])
                stack = env.copy()
                exec(Path(module_path, "stack.py").read_text(), stack)
                self._cache[module_name]["stack"] = stack

                # read pre/post deploy code
                pre_post_actions_path = Path(module_path, "pre_post_actions.py")
                if pre_post_actions_path.exists():
                    pre_post_code = env.copy()
                    exec(pre_post_actions_path.read_text(), pre_post_code)
                    self._cache[module_name] = {
                        **self._cache[module_name],
                        **{k: pre_post_code[k] for k in pre_post_code.keys() & {"pre_deploy", "pre_destroy"}},
                    }

    def __setitem__(self, key, value):
        raise RuntimeError()

    def __getitem__(self, item):
        self._populate_cache()
        return self._cache.get(item)

    def __len__(self):
        self._populate_cache()
        return len(self._cache)

    def keys(self):
        self._populate_cache()
        return self._cache.keys()

    def values(self):
        self._populate_cache()
        return self._cache.values()

    def items(self):
        self._populate_cache()
        return self._cache.items()

    def enabled(self):
        enabled = self.cfg.get(self.CFG_KEY, value_type=set)
        return {mod_key: info for mod_key, info in self.items() if mod_key in enabled}

    def disabled(self):
        enabled = self.cfg.get(self.CFG_KEY, value_type=set)
        return {mod_key: info for mod_key, info in self.items() if mod_key not in enabled}
