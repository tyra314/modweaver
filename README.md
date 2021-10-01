# modweaver
A Minecraft CLI mod manager using Modrinth AND CurseForge

## Installation

I recommend to create a new virtualenv and use pip to install modweaver.

```
git clone https://github.com/tyra314/modweaver.git
cd modweaver

pip install -U virtualenv
python -m venv venv

# On Linux and MacOS
. venv/bin/activate

# ... or on Windows:
.\venv\Scripts\activate

pip install .
```

### Modrinth Authentification

Modrinth requires you to provide a GitHub OAuth token to access their API.
You can get one with your GitHub account:

1. Visit this page: https://github.com/settings/tokens
2. Select `Personal access tokens`
3. Generate a token with `read:user` and `user:email` scopes
4. Provide the token to modweaver using `--modrinth-token` or the environment variable `MODRINTH_TOKEN`


## Getting started

The first step is to create a new mod environment. For that, we use the `init` command
and provide the Minecraft version and Modloader. For example:

```
cd /path/to/minecraft/mods
modweaver init 1.17.1 fabric
```

This creates the file `.mods.toml`, which modweaver uses to store information about the tracked mods.

If there are already mods in the folder, we can ask modweaver to track those.

```
modweaver --mr discover *.jar
modweaver --cf discover *.jar
```

> In the above example, if a mod was found using the first call with Modrinth backend, modweaver won't try to find it during the second call with CurseForge

We can get a list of all currently tracked mods:

```
modweaver list
```

Now, we can start adding mods as well:

```
modweaver --mr add Abc12345
modweaver --cf add 123456
```

Or remove mods:

```
modweaver remove Abc12345
modweaver remove 123456
```

If we need to know everything about a mod, the `info` command is our friend:

```
modweaver --mr info Abc12345
modweaver --cf info 123456
```

## Upgrade mods

We can also upgrade mods. First, let us look for outdated mods:

```
modweaver --mr outdated
modweaver --cf outdated
```

And to upgrade all mods, we can use:

```
modweaver --mr upgrade
modweaver --cf upgrade
```

Or, we can also upgrade specific mods only:

```
modweaver --mr upgrade Abc12345
modweaver --cf upgrade 123456
```

## Downgrade mods

We can also roll back to a different version of the mod. The `versions` command can list compatible or even all versions for a given mod:

```
modweaver --mr versions Abc12345
modweaver --cf versions 123456
```

Using the mod id and version id, we can install the desired version:

```
modweaver --mr versions Abc12345 DEFG5467
modweaver --cf versions 123456 789101112
```

## Search for mods

The Modrinth backend also allows to search for mods matching a search term *and* the current mod environment.

```
modweaver --mr search Fabric
```

## Mod downloading backends

Modweaver supports Modrinth and curseforge as backend for downloading mods.
You need to manually switch between the backends using the `--provider` option.
Modweaver also accepts the shorthands `--modrinth`, `--mr`, `--curseforge`, and `--cf`.

## Limitations

- The output could be improved for some commands, if no mods were affected
- The mod backend could be more transparent, some commands should use both, e.g., upgrade, outdated
- Downloading dependencies of mods isn't implemented yet
- There's no progress bar :(
- Don't manually update or remove mods that are tracked by Modweaver, it will be confused.