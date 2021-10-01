import traceback

import click

from .config import Config
from .mod import DetailedMod, InstalledMod, Mod, ModVersion


def print_mod(mod: DetailedMod) -> None:
    click.secho(" ~~~ ", nl=False)
    click.secho(mod.name, fg="bright_green", nl=False)
    click.secho(" by ", nl=False)
    click.secho(mod.author, fg="red", nl=False)
    click.secho(" ~~~ ")

    click.echo()

    click.secho("Website: ", nl=False)
    click.secho(mod.website, fg="yellow")

    click.echo()

    click.secho("Description: ", nl=False)
    click.secho(mod.description, fg="bright_black")

    click.secho("Categories: ", nl=False)
    click.secho(", ".join(mod.categories))

    click.secho("Game Versions: ", nl=False)
    click.secho(", ".join(mod.game_versions))

    click.secho("Loaders: ", nl=False)
    click.secho(", ".join(mod.loaders))

    click.echo()

    click.secho("Downloads: ", nl=False)
    click.secho(str(mod.downloads))

    if mod.source_url:
        click.secho("Source: ", nl=False)
        click.secho(mod.source_url)

    if mod.issues_url:
        click.secho("Issues: ", nl=False)
        click.secho(mod.issues_url)


def print_mod_concise(mod: Mod) -> None:
    click.secho("- ", nl=False)
    click.secho(mod.id, fg="red", nl=False)
    click.secho(": ", nl=False)
    click.secho(mod.name, fg="bright_green", nl=False)
    click.secho(" - ", nl=False)
    click.secho(mod.description, fg="bright_black")


def print_installed_mod(mod: InstalledMod) -> None:
    click.secho("- ", nl=False)
    click.secho(mod.id, fg="red", nl=False)
    click.secho(": ", nl=False)
    click.secho(mod.name, fg="bright_green", nl=False)
    click.secho(" - ", nl=False)
    click.secho(mod.installed_version, nl=False)
    click.secho(
        f" ({mod.installed_file})",
        fg="bright_black",
    )


def print_mod_version(version: ModVersion) -> None:
    click.secho("- ", nl=False)
    click.secho(version.id, fg="red", nl=False)
    click.secho(": ", nl=False)
    click.secho(version.version, fg="bright_green", nl=False)
    click.secho(" - ", nl=False)
    click.secho(version.filename, nl=False)
    click.secho(
        f" (from {version.date})",
        fg="bright_black",
    )


def print_config(config: Config) -> None:
    click.secho(" ~~~ Minecraft ", nl=False)
    click.secho(config.version, fg="bright_green", nl=False)
    click.secho(" using ", nl=False)
    click.secho(config.loader, fg="red", nl=False)
    click.secho(" Modloader ~~~ ")

    click.echo()

    for mod in config.mods.values():
        print_installed_mod(mod)


def print_error_message(ctx: click.Context, e: Exception) -> None:
    if ctx.obj["DEBUG"]:
        print(traceback.format_exc())
    click.secho("Error: ", nl=False, fg="red")
    click.secho(str(e))
