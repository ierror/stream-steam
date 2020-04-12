from collections import defaultdict
from importlib import import_module
from pathlib import Path


class Modules(dict):
    CFG_KEY = "modules_enabled"
    _cache = defaultdict(lambda: None)

    def __init__(self, cfg):
        self.cfg = cfg

    def _populate_cache(self):
        # read and cache module info
        modules_path = Path("modules/")
        for module_path in [p for p in modules_path.iterdir() if p.is_dir() and p.name not in ["__pycache__"]]:
            # e.g. modules/spark_cluster => spark_cluster
            module_id = module_path.name
            module = import_module(f"modules.{module_id}.manifest")
            self._cache[module_id] = module.Manifest

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
