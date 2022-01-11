import os
from contextlib import suppress
from typing import Dict

import toml
from dacite.core import from_dict

from .mod import InstalledMod


class Config(object):
    def __init__(self, file: str, version: str, loader: str):
        self.file = file
        self.version = version
        self.loader = loader
        self.mods: Dict[str, InstalledMod] = {}

    @classmethod
    def init(cls, file: str, version: str, loader: str) -> "Config":
        if not os.path.exists(file):
            return Config(file=file, version=version, loader=loader).save()
        else:
            raise ValueError("Config file does already exist.")

    @classmethod
    def load_from(cls, file: str) -> "Config":
        data = toml.load(file)

        config = Config(file=file, version=data["version"], loader=data["loader"])

        for mod in data["mods"]:
            config.add_mod(from_dict(data_class=InstalledMod, data=mod))

        return config

    def save(self) -> "Config":
        with open(self.file, "w") as f:
            toml.dump(
                {
                    "version": self.version,
                    "loader": self.loader,
                    "mods": [mod.asdict() for mod in self.mods.values()],
                },
                f,
            )

        return self

    def disable(self, mod: InstalledMod) -> None:
        with suppress(FileNotFoundError):
            os.rename(
                mod.installed_file,
                f"{mod.installed_file}.disabled",
            )

    def enable(self, mod: InstalledMod) -> None:
        with suppress(FileNotFoundError):
            os.rename(
                f"{mod.installed_file}.disabled",
                mod.installed_file,
            )

    def add_mod(self, mod: InstalledMod) -> None:
        self.mods[mod.id] = mod

    def remove_mod(self, modid: str) -> None:
        assert modid in self.mods
        with suppress(FileNotFoundError):
            os.remove(self.mods[modid].installed_file)
        with suppress(KeyError):
            del self.mods[modid]

    def is_mod_installed(self, modid: str) -> bool:
        return modid in self.mods.keys()

    def is_file_known(self, file: str) -> bool:
        return any([mod.installed_file == file for mod in self.mods.values()])
