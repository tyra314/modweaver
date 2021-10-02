import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    List,
    Optional,
    Tuple,
)

import click
import click_completion  # type: ignore[import]
import click_log  # type: ignore[import]

from .config import Config
from .format import (
    print_config,
    print_error_message,
    print_installed_mod,
    print_mod,
    print_mod_concise,
    print_mod_version,
)
from .mod import InstalledMod, ModVersion
from .provider import ModProvider, ReverseSearchableModProvider, SearchableModProvider

click_completion.init()

logger = logging.getLogger(__name__)
click_log.basic_config(logger)


def coroutine(f: Callable[..., Awaitable[None]]) -> Callable[..., None]:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        asyncio.run(f(*args, **kwargs))

    return wrapper


def handle_exceptions(f: Callable[..., None]) -> Callable[..., None]:
    @wraps(f)
    def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> None:
        try:
            return f(ctx, *args, **kwargs)
        except Exception as e:
            print_error_message(ctx, e)

    return wrapper


@contextmanager
def load_or_fail(ctx: click.Context) -> Generator[Config, None, None]:
    config = Config.load_from(ctx.obj["CONFIG"])

    yield config

    config.save()


@asynccontextmanager
async def provider(
    ctx: click.Context, config: Config
) -> AsyncGenerator[ModProvider, None]:
    from .curse import CurseForgeAPI
    from .modrinth import ModrinthAPI

    provider = ctx.obj["PROVIDER"]

    if provider == "modrinth":
        token = ctx.obj["MODRINTH_TOKEN"]

        if not token:
            raise ValueError(
                "Missing token for Modrinth. (Set using --modrinth-token or environment variable MODRINTH_TOKEN)"
            )

        async with ModrinthAPI(token=token, config=config) as mapi:
            yield mapi
    elif provider == "curseforge":
        async with CurseForgeAPI(config=config) as cfapi:
            yield cfapi
    else:
        raise ValueError(f"Unsupported provider selected: {provider}")


@click.group()
@click.option(
    "-d",
    "--debug",
    help="print exception stacks",
    is_flag=True,
    default=False,
)
@click.option(
    "-c",
    "--config-file",
    help="alternate .mods.toml",
    default=".mods.toml",
    type=click.Path(),
)
@click.option(
    "--curseforge",
    "provider",
    help="Use CurseForge to download mods from",
    flag_value="curseforge",
)
@click.option(
    "--cf",
    "provider",
    help="Use CurseForge to download mods from",
    flag_value="curseforge",
)
@click.option(
    "--modrinth",
    "provider",
    help="Use Modrinth to download mods from",
    flag_value="modrinth",
)
@click.option(
    "--mr",
    "provider",
    help="Use Modrinth to download mods from",
    flag_value="modrinth",
)
@click.option(
    "--modrinth-token",
    help="The GitHub OAuth Access Token for Modrinth authentification",
    envvar="MODRINTH_TOKEN",
)
@click.option(
    "-p",
    "--provider",
    help="Select the source for downloading mods from",
    default="modrinth",
    type=click.Choice(["modrinth", "curseforge"], case_sensitive=False),
)
@click_log.simple_verbosity_option(logger)  # type: ignore
@click.pass_context
def cli(
    ctx: click.Context,
    config_file: str,
    debug: bool,
    provider: str,
    modrinth_token: Optional[str],
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["CONFIG"] = config_file
    ctx.obj["DEBUG"] = debug
    ctx.obj["PROVIDER"] = provider
    ctx.obj["MODRINTH_TOKEN"] = modrinth_token


@cli.command(short_help="initialize a new mod list")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite any existing modlist files",
)
@click.argument(
    "game_version",
    required=True,
)
@click.argument(
    "mod_loader",
    required=True,
    type=click.Choice(["fabric", "forge"], case_sensitive=False),
)
@click.pass_context
@handle_exceptions
@coroutine
async def init(
    ctx: click.Context, game_version: str, mod_loader: str, force: bool
) -> None:
    file = ctx.obj["CONFIG"]
    if force:
        from pathlib import Path

        Path(file).unlink(missing_ok=True)
    Config.init(file, version=game_version, loader=mod_loader)
    print("Initialized.")


@cli.command(short_help="Search for matching mods")
@click.argument(
    "query",
    required=True,
)
@click.pass_context
@handle_exceptions
@coroutine
async def search(ctx: click.Context, query: str) -> None:
    with load_or_fail(ctx) as config:
        async with provider(ctx, config) as api:
            if isinstance(api, SearchableModProvider):
                async for mod in api.search(query):
                    print_mod_concise(mod)
            else:
                print_error_message(
                    ctx,
                    RuntimeError(
                        f"The selected provider ({api.provider_id}) does not support search."
                    ),
                )


@cli.command(short_help="show details for the given mod")
@click.argument("mod", required=True)
@click.pass_context
@handle_exceptions
@coroutine
async def info(ctx: click.Context, mod: str) -> None:
    with load_or_fail(ctx) as config:
        async with provider(ctx, config) as api:
            info = await api.detailed_info(mod)
            print_mod(info)


@cli.command(short_help="download one or more mods")
@click.argument("mod_ids", required=True, nargs=-1, type=click.STRING)
@click.pass_context
@handle_exceptions
@coroutine
async def add(ctx: click.Context, mod_ids: List[str]) -> None:
    print("Installed: ")
    with load_or_fail(ctx) as config:
        async with provider(ctx, config) as api:
            for mod in asyncio.as_completed([api.add(modid) for modid in mod_ids]):
                try:
                    print_installed_mod(await mod)
                except Exception as e:
                    print_error_message(ctx, e)


@cli.command(short_help="delete one or more mods")
@click.argument("mod_ids", nargs=-1, type=click.STRING)
@click.option("-a", "--all", is_flag=True, default=False)
@click.pass_context
@handle_exceptions
@coroutine
async def remove(ctx: click.Context, mod_ids: List[str], all: bool) -> None:
    with load_or_fail(ctx) as config:
        async with provider(ctx, config) as api:
            if all and not mod_ids:
                mod_ids = list(config.mods.keys())

            for modid in mod_ids:
                info = await api.info(modid)
                if config.is_mod_installed(info.id):
                    mod = config.mods[info.id]
                    config.remove_mod(info.id)
                    print(f"Deleted '{mod.installed_file}' ({info.id})")
                else:
                    print_error_message(
                        ctx,
                        RuntimeError(
                            f"Cannot remove the mod '{info.name}' ({info.id}). It isn't installed."
                        ),
                    )


@cli.command(short_help="update one or more mods")
@click.argument("mod_ids", nargs=-1, type=click.STRING)
@click.pass_context
@handle_exceptions
@coroutine
async def upgrade(ctx: click.Context, mod_ids: List[str]) -> None:
    print("Upgraded: ")
    with load_or_fail(ctx) as config:
        async with provider(ctx, config) as api:
            if not mod_ids:
                mod_ids = [
                    mod.id
                    for mod in config.mods.values()
                    if mod.provider_id == api.provider_id
                ]

            for mod in asyncio.as_completed([api.upgrade(modid) for modid in mod_ids]):
                try:
                    upgrade = await mod
                    if upgrade:
                        print_installed_mod(upgrade)
                except Exception as e:
                    print_error_message(ctx, e)


@cli.command("list", short_help="print the mod list to stdout")
@click.pass_context
@handle_exceptions
@coroutine
async def run_list(ctx: click.Context) -> None:
    with load_or_fail(ctx) as config:
        print_config(config)


@cli.command(short_help="list the mods that can be upgraded")
@click.pass_context
@handle_exceptions
@coroutine
async def outdated(ctx: click.Context) -> None:
    with load_or_fail(ctx) as config:
        async with provider(ctx, config) as api:

            async def zipper(
                mod: InstalledMod, coro: Awaitable[Optional[ModVersion]]
            ) -> Tuple[InstalledMod, Optional[ModVersion]]:
                return (mod, await coro)

            for coro in asyncio.as_completed(
                [
                    zipper(mod, api.find_upgrade(mod))
                    for mod in config.mods.values()
                    if mod.provider_id == api.provider_id
                ]
            ):
                try:
                    mod, available_upgrade = await coro
                    if available_upgrade:
                        print(
                            f"{mod.id}: '{mod.name}' can be updated from '{mod.installed_version}'  to '{available_upgrade.version}'"
                        )
                    else:
                        print(f"{mod.id}: '{mod.name}' is up-to-date.")
                except Exception as e:
                    print_error_message(ctx, e)


@cli.command(short_help="Try to identify the given files and add them to the config")
@click.argument("mod_files", required=True, nargs=-1, type=click.STRING)
@click.pass_context
@handle_exceptions
@coroutine
async def discover(ctx: click.Context, mod_files: List[str]) -> None:
    print("Found mods: ")
    with load_or_fail(ctx) as config:
        async with provider(ctx, config) as api:
            if isinstance(api, ReverseSearchableModProvider):
                for mod in asyncio.as_completed(
                    [
                        api.discover(file)
                        for file in mod_files
                        if not config.is_file_known(file)
                    ]
                ):
                    try:
                        print_installed_mod(await mod)
                    except Exception as e:
                        print_error_message(ctx, e)
            else:
                print_error_message(
                    ctx,
                    RuntimeError(
                        f"The selected provider ({api.provider_id}) does not support discover."
                    ),
                )


@cli.command(short_help="list all compatible version for the given mod")
@click.option(
    "-a",
    "--all",
    is_flag=True,
    default=False,
    help="List all available versions (the list might be VERY long)",
)
@click.argument("mod", required=True)
@click.pass_context
@handle_exceptions
@coroutine
async def versions(ctx: click.Context, mod: str, all: bool) -> None:
    with load_or_fail(ctx) as config:
        async with provider(ctx, config) as api:
            info = await api.detailed_info(mod)

            for version in info.versions if all else info.matching_versions(config):
                print_mod_version(version)


@cli.command(short_help="install the given version of a mod")
@click.argument("mod_id", required=True, type=click.STRING)
@click.argument("version_id", required=True, type=click.STRING)
@click.pass_context
@handle_exceptions
@coroutine
async def install(ctx: click.Context, mod_id: str, version_id: str) -> None:
    print("Installed: ")
    with load_or_fail(ctx) as config:
        async with provider(ctx, config) as api:
            info = await api.detailed_info(mod_id)

            try:
                for version in info.matching_versions(config):
                    if version.id == version_id:
                        installed_version = await api.download(info, version)

                        if config.is_mod_installed(mod_id):
                            config.remove_mod(mod_id)

                        print_installed_mod(installed_version)

                        config.add_mod(installed_version)

            except Exception as e:
                print_error_message(ctx, e)
