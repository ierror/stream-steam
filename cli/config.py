import os
from configparser import ConfigParser
from pathlib import Path

from cached_property import cached_property


class ConfigManager:
    _cfg = dict()

    def __init__(self, env):
        self._env = env
        self.read()

    @cached_property
    def file(self):
        return os.path.join(str(Path.home()), ".stream-steam.cfg")

    def get(self, key):
        return self._cfg.get(key)

    def set(self, key, value):
        self._cfg[key] = value

    def read(self):
        cfg = ConfigParser()
        cfg.read(self.file)
        try:
            self._cfg = cfg[self._env]
        except KeyError:
            pass  # keep empty dict

    def write(self):
        config = ConfigParser()
        config.add_section(self._env)

        for key, value in self._cfg.items():
            config[self._env][key] = value
        with open(self.file, "w") as fh:
            config.write(fh)
