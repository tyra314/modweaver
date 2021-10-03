from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional

from .config import Config
from .mod import DetailedMod, InstalledMod, Mod, ModVersion


class ModProvider(ABC):
    def __init__(self, config: Config, **kwargs: Any):
        self.config = config

    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    async def add(self, modid: str) -> InstalledMod:
        info = await self.detailed_info(modid)

        if self.config.is_mod_installed(info.id):
            raise RuntimeError(f"The mod with id '{modid}' is already installed.")

        versions = info.matching_versions(self.config)

        if not versions:
            raise RuntimeError(
                f"Couldn't find any matching versions to install for the mod with id '{modid}'"
            )

        try:
            installed_mod = await self.download(info, versions[0])
        except Exception as e:
            raise RuntimeError(
                f"Couldn't download version {versions[0].version} of the mod with id '{modid}'"
            ) from e

        self.config.add_mod(installed_mod)

        return installed_mod

    async def find_upgrade(self, mod: InstalledMod) -> Optional[ModVersion]:
        info = await self.detailed_info(mod.id)

        versions = info.matching_versions(self.config)

        if not versions:
            raise RuntimeError(
                f"Couldn't find any matching versions to install for the mod '{info.name}' ({info.id})"
            )

        if versions[0].id == mod.version_id:
            return None
        else:
            return versions[0]

    async def upgrade(self, modid: str) -> Optional[InstalledMod]:
        info = await self.info(modid)

        if not self.config.is_mod_installed(info.id):
            raise RuntimeError(f"The mod with id '{modid}' is not installed.")

        installed_mod = self.config.mods[info.id]

        if installed_mod.pinned:
            return None

        upgrade_version = await self.find_upgrade(installed_mod)

        if upgrade_version:
            try:
                mod = await self.download(info, upgrade_version)
            except Exception as e:
                raise RuntimeError(
                    f"Couldn't download version {upgrade_version.version} of the mod with id '{modid}'"
                ) from e

            self.config.remove_mod(installed_mod.id)
            self.config.add_mod(mod)

            return mod
        else:
            # raise RuntimeError(
            #     f"Couldn't find a suitable upgrade for version {installed_mod.installed_version} of the mod '{info.name}' ({info.id})"
            # )
            return None

    @abstractmethod
    async def download(self, mod: Mod, version: ModVersion) -> InstalledMod:
        pass

    @abstractmethod
    async def info(self, modid: str) -> Mod:
        pass

    @abstractmethod
    async def detailed_info(self, modid: str) -> DetailedMod:
        pass


class SearchableModProvider(ModProvider):
    @abstractmethod
    async def search(self, name: str) -> AsyncGenerator[Mod, None]:
        if False:
            yield


class ReverseSearchableModProvider(ModProvider):
    @abstractmethod
    async def discover(self, file: str) -> InstalledMod:
        pass
