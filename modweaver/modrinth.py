import asyncio
import hashlib
from typing import Any, AsyncGenerator, Dict, List, cast

import aiofiles
from aiohttp import ClientResponseError
from dateutil.parser import isoparse

from .mod import DetailedMod, InstalledMod, Mod, ModVersion
from .provider import ReverseSearchableModProvider, SearchableModProvider
from .remote import RemoteAPI


class ModrinthRemoteAPI(RemoteAPI):
    @property
    def base_url(self) -> str:
        return "https://api.modrinth.com/api/v1/"


class ModrinthAPI(
    ModrinthRemoteAPI, SearchableModProvider, ReverseSearchableModProvider
):
    @property
    def provider_id(self) -> str:
        return "modrinth"

    async def __aenter__(self) -> "ModrinthAPI":
        return cast("ModrinthAPI", await super().__aenter__())

    async def _load_version_info(self, version: str) -> ModVersion:
        return self.parse_json_to_version(await self._get(f"version/{version}"))

    def parse_json_to_version(self, data: Dict[str, Any]) -> ModVersion:
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

    async def info(self, modid: str) -> Mod:
        try:
            hit = await self._get(f"mod/{modid}")
        except ClientResponseError as e:
            raise KeyError(f"Couldn't find a mod with id '{modid}'") from e

        slug = hit["slug"] if hit["slug"] else modid

        return Mod(
            id=hit["id"],
            name=hit["title"],
            author="",
            website=f"https://modrinth.com/mod/{slug}",
            description=hit["description"],
            categories=list(set(hit["categories"])),
        )

    async def detailed_info(self, modid: str) -> DetailedMod:
        try:
            hit = await self._get(f"mod/{modid}")
        except ClientResponseError as e:
            raise KeyError(f"Couldn't find a mod with id '{modid}'") from e

        try:
            slug = hit["slug"] if hit["slug"] else modid
            team_members: List[Dict[str, str]] = cast(
                List[Dict[str, str]], await self._get(f"team/{hit['team']}/members")
            )
            users = await asyncio.gather(
                *[self._get(f"user/{user['user_id']}") for user in team_members]
            )
            versions = await asyncio.gather(
                *[self._load_version_info(version) for version in hit["versions"]]
            )
        except ClientResponseError as e:
            raise RuntimeError(
                f"Couldn't properly load information for the mod with id '{modid}'"
            ) from e

        return DetailedMod(
            id=hit["id"],
            name=hit["title"],
            author=", ".join(
                user["name"] if user["name"] else user["username"] for user in users
            ),
            website=f"https://modrinth.com/mod/{slug}",
            description=hit["description"],
            categories=list(set(hit["categories"])),
            issues_url=hit["issues_url"] if "issues_url" in hit else None,
            source_url=hit["source_url"] if "source_url" in hit else None,
            downloads=hit["downloads"],
            versions=versions,
        )

    async def search(self, name: str) -> AsyncGenerator[Mod, None]:
        mod_data = await self._get(
            "mod",
            params={
                "query": name,
                "facets": f'[["versions:{self.config.version}"],["categories:{self.config.loader}"]]',
            },
        )

        for hit in mod_data["hits"]:
            yield Mod(
                id=hit["mod_id"].replace("local-", ""),
                name=hit["title"],
                author=hit["author"],
                website=hit["page_url"],
                description=hit["description"],
                categories=list(set(hit["categories"])),
            )

    async def download(self, mod: Mod, version: ModVersion) -> InstalledMod:
        assert self._session is not None
        async with self._session.get(version.url) as resp:
            async with aiofiles.open(version.filename, mode="wb") as f:
                await f.write(await resp.read())

        return InstalledMod.from_version(mod.name, version, provider=self.provider_id)

    async def file_hash(self, file: str) -> str:
        sha1 = hashlib.sha1()

        async with aiofiles.open(file, "rb") as f:
            async for chunk in f:
                sha1.update(chunk)

        return sha1.hexdigest().lower()

    async def discover(self, file: str) -> InstalledMod:
        sha = await self.file_hash(file)

        try:
            data = await self._get(f"version_file/{sha}?algorithm=sha1")
            version = self.parse_json_to_version(data)

            info = await self.info(version.modid)

            installed_mod = InstalledMod.from_version(
                modname=info.name, version=version, provider=self.provider_id
            )

            self.config.add_mod(installed_mod)

            return installed_mod

        except ClientResponseError as e:
            raise RuntimeError(f"Couldn't identify the mod in the file '{file}'") from e
