from typing import Any, Dict, List, Optional, cast
from contextlib import suppress

import aiohttp
from aiohttp import ClientResponseError
import aiofiles

from .config import Config
from .mod import DetailedMod, InstalledMod, Mod, ModVersion
from .murmur2 import murmur2
from .provider import ReverseSearchableModProvider
from .remote import RemoteAPI


class CurseForgeRemoteAPI(RemoteAPI):
    @property
    def base_url(self) -> str:
        return "https://addons-ecs.forgesvc.net/api/v2/"


class CurseForgeAPI(CurseForgeRemoteAPI, ReverseSearchableModProvider):
    def __init__(self, config: Config):
        self.config = config

    @property
    def provider_id(self) -> str:
        return "curseforge"

    async def __aenter__(self) -> "CurseForgeAPI":
        return cast("CurseForgeAPI", await super().__aenter__())

    async def download(self, mod: Mod, version: ModVersion) -> InstalledMod:
        assert self._session is not None
        async with self._session.get(version.url) as resp:
            async with aiofiles.open(version.filename, mode="wb") as file:
                await file.write(await resp.read())

        return InstalledMod.from_version(mod.name, version, provider=self.provider_id)

    async def info(self, modid: str) -> Mod:
        try:
            hit = await self._post("addon", json=[modid])
            hit = cast(List[Dict[str, Any]], hit)[0]
        except (ClientResponseError, IndexError) as e:
            raise KeyError(f"Couldn't find a mod with id '{modid}'") from e

        return Mod(
            id=str(hit["id"]),
            name=hit["name"],
            author=", ".join(author["name"] for author in hit["authors"]),
            website=hit["websiteUrl"],
            description=hit["summary"],
            categories=[category["name"] for category in hit["categories"]],
        )

    async def detailed_info(self, modid: str) -> DetailedMod:
        try:
            hit = await self._post("addon", json=[modid])
            hit = cast(List[Dict[str, Any]], hit)[0]

            files = await self._get(f"addon/{modid}/files")
        except (ClientResponseError, IndexError) as e:
            raise KeyError(f"Couldn't find a mod with id '{modid}'") from e

        versions = []

        for entry in cast(List[Dict[str, Any]], files):
            loaders = []

            if "Fabric" in entry["gameVersion"]:
                loaders.append("fabric")

            if "Forge" in entry["gameVersion"]:
                loaders.append("forge")

            if not loaders:
                # in ye ol' days, there was only forge
                loaders.append("forge")

            versions.append(
                ModVersion(
                    id=str(entry["id"]),
                    modid=modid,
                    version=entry["displayName"],
                    filename=entry["fileName"],
                    url=entry["downloadUrl"],
                    date=entry["fileDate"],
                    loaders=loaders,
                    game_versions=[
                        version
                        for version in entry["gameVersion"]
                        if version != "Fabric" and version != "Forge"
                    ],
                )
            )

        return DetailedMod(
            id=str(hit["id"]),
            name=hit["name"],
            author=", ".join(author["name"] for author in hit["authors"]),
            website=hit["websiteUrl"],
            description=hit["summary"],
            categories=[category["name"] for category in hit["categories"]],
            issues_url=hit["issueTrackerUrl"] if "issueTrackerUrl" in hit else None,
            source_url=hit["sourceUrl"] if "sourceUrl" in hit else None,
            downloads=int(hit["downloadCount"]),
            versions=versions,
        )

    async def file_hash(self, file: str) -> int:
        async with aiofiles.open(file, "rb") as f:
            data = await f.read()
        data = bytes([b for b in data if b not in (9, 10, 13, 32)])
        return murmur2(data=data, seed=1)

    def guess_name(self, file: str) -> str:
        return file.split("-")[0].split("_")[0]

    async def discover(self, file: str) -> InstalledMod:
        fingerprint = await self.file_hash(file)

        try:
            response = await self._post("fingerprint", json=[fingerprint])
        except ClientResponseError as e:
            raise RuntimeError(f"Couldn't identify the mod in the file '{file}'") from e

        if len(response["exactMatches"]) > 0:
            match = response["exactMatches"][0]

            info = None
            with suppress(KeyError):
                info = await self.info(match["id"])

            installed_mod = InstalledMod(
                id=str(match["id"]),
                name=info.name
                if info
                else self.guess_name(match["file"]["displayName"]),
                version_id=str(match["file"]["id"]),
                installed_version=match["file"]["displayName"],
                installed_file=file,
                source_url=match["file"]["downloadUrl"],
                provider_id=self.provider_id,
            )

            self.config.add_mod(installed_mod)

            return installed_mod
        else:
            raise RuntimeError(f"Couldn't identify the mod in the file '{file}'")
