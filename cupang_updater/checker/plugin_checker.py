import json
import zipfile
from pathlib import Path
from typing import Any

import strictyaml as sy
import toml

jar_yaml_schema = sy.MapCombined(
    {
        sy.Optional("name"): sy.Str(),
        sy.Optional("version"): sy.Str() | sy.Seq(sy.Str()),
        sy.Optional("authors"): sy.Seq(sy.Str()),
        sy.Optional("author"): sy.Str(),
    },
    sy.Str(),
    sy.Any(),
)


def jar_info(path: Path) -> tuple[str, str, str | None]:
    """
    return name, version, authors
    """
    path: Path = Path(path) if path is not Path else path
    if path.suffix != ".jar":
        raise ValueError("Invalid file, expected .jar")
    jar = zipfile.ZipFile(path)
    config: dict[str, Any]
    jar_name: str = None
    jar_version: str = None
    jar_authors: str | list[str] = None

    # Bukkit (paper too)
    bukkit_ymls = [
        "paper-plugin.yml",
        "plugin.yml",
        "bungee.yml",
    ]
    if any(item in jar.namelist() for item in bukkit_ymls):
        for bukkit_yml in bukkit_ymls:
            if bukkit_yml in jar.namelist():
                j = jar.open(bukkit_yml, "r")
                break

        config = sy.dirty_load(j.read().decode(), schema=jar_yaml_schema, allow_flow_style=True).data

        jar_name = config.get("name")
        jar_version = config.get("version")
        jar_authors = config.get("authors", config.get("author"))

        j.close()

    # Velocity
    elif "velocity-plugin.json" in jar.namelist():
        with jar.open("velocity-plugin.json", "r") as j:
            config = json.load(j)

            jar_name = config.get("name", config.get("id"))
            jar_version = config.get("version")
            jar_authors = config.get("authors")

    # Fabric
    elif "fabric.mod.json" in jar.namelist():
        with jar.open("fabric.mod.json", "r") as j:
            config = json.load(j)

            jar_name = config.get("name", config.get("id"))
            jar_version = config.get("version")
            jar_authors = config.get("authors")

    # Forge
    elif "META-INF/mods.toml" in jar.namelist():
        with jar.open("META-INF/mods.toml", "r") as j:
            config = toml.loads(j.read().decode())

            jar_name = config["mods"][0]["modId"] if config.get("mods") else None
            jar_version = config["mods"][0]["version"] if config.get("mods") else None
            jar_authors = config["mods"][0]["authors"] if config.get("mods") else None

    # Ensure authors are represent in list
    if isinstance(jar_authors, str):
        jar_authors = list([jar_authors])

    # safe operation if jar_version is empty
    jar_version = jar_version or 0

    # some dev put version in a list instead of just string which make things broke
    # e.g [1.0]
    if isinstance(jar_version, list):
        jar_version = jar_version[0]

    jar_version = str(jar_version)

    return jar_name, jar_version, jar_authors
