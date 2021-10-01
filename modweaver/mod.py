from datetime import datetime

from dateutil.parser import isoparse

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, cast

from . import config


@dataclass
class ModVersion:
    id: str
    modid: str
    version: str
    filename: str
    url: str
    date: datetime
    loaders: List[str] = field(default_factory=list)
    game_versions: List[str] = field(default_factory=list)

    @staticmethod
    def from_json(data: Dict[str, Any]) -> "ModVersion":
        return ModVersion(
            id=data["id"],
            modid=data["mod_id"],
            version=data["version_number"],
            filename=data["files"][0]["filename"],
            url=data["files"][0]["url"],
            loaders=data["loaders"],
            game_versions=data["game_versions"],
            date=isoparse(data["date_published"]),
        )

    def matches(self, config: "config.Config") -> bool:
        return config.version in self.game_versions and config.loader in self.loaders


@dataclass
class InstalledMod:
    id: str
    name: str
    version_id: str
    installed_version: str
    installed_file: str
    source_url: str
    provider_id: str = "modrinth"

    def asdict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_version(
        cls, modname: str, version: ModVersion, provider: str
    ) -> "InstalledMod":
        return InstalledMod(
            id=version.modid,
            name=modname,
            version_id=version.id,
            installed_file=version.filename,
            installed_version=version.version,
            source_url=version.url,
            provider_id=provider,
        )


@dataclass
class Mod:
    id: str
    name: str
    author: str
    website: str
    description: str
    categories: Sequence[str]


@dataclass
class DetailedMod(Mod):
    issues_url: Optional[str]
    source_url: Optional[str]
    downloads: int
    versions: Sequence[ModVersion]

    @property
    def loaders(self) -> Sequence[str]:
        loaders: Set[str] = set()
        for version in self.versions:
            for loader in version.loaders:
                loaders.add(loader)

        return sorted(loaders)

    @property
    def game_versions(self) -> Sequence[str]:
        game_versions: Set[str] = set()
        for version in self.versions:
            for game_version in version.game_versions:
                game_versions.add(game_version)

        return sorted(game_versions)

    @property
    def sorted_versions(self) -> List[ModVersion]:
        return sorted(self.versions, key=lambda x: x.date, reverse=True)

    def matching_versions(self, config: "config.Config") -> List[ModVersion]:
        return [version for version in self.sorted_versions if version.matches(config)]
