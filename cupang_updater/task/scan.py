import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import strictyaml as sy

from ..app.app_config import app_status
from ..checker import jar_info
from ..cmd.cmd_opt import args
from ..config import Config
from ..logger import LoggerManager
from ..manager.updater_manager import UpdaterManager
from ..utils import FileHash
from ..utils.common import reindent

log = LoggerManager().get_log()


def update_from_default(data1: sy.YAML, data2: sy.YAML, name: str = None):
    if args.config_cleanup:
        # Remove keys from data1 that are not in data2
        for key in list(data1.keys()):
            if key not in data2.data:
                log.info(f"[red]Removing key {key}" + f" from {name}" if name else "")
                del data1[key]

    # Add keys to data1 that are present in data2 but not in data1
    for key in list(data2.keys()):
        if key not in data1.data:
            log.info(f"[green]Adding key {key}" + f" for {name}" if name else "")
            data1[key] = data2[key]

    return data1


def scan_plugins(config: Config) -> None | Any:
    updater_manager = UpdaterManager()
    plugins_folder = Path(config.get("settings.server_folder").data, "plugins")
    is_new_plugin = False

    # many thing happens here
    # i can't blindly update YAML object to the config, because its too slow
    # so instead, i guarantee that plugins_config is type of dict[str, YAML]
    plugins_config: sy.YAML = deepcopy([config.get("plugins")])[0]
    if plugins_config.data:
        _plugins_config = {}
        for k in plugins_config.data.keys():
            _plugins_config[k] = plugins_config[k]
        plugins_config = _plugins_config
    else:
        plugins_config = plugins_config.data
    # ensure the typing
    plugins_config: dict[str, sy.YAML] = plugins_config

    def status_update(msg: str, log_type: str = "info", no_log: bool = False):
        app_status.update(msg)
        if not no_log:
            match log_type.lower():
                case "error":
                    log.error(app_status.status)
                case "warning":
                    log.warning(app_status.status)
                case _:
                    log.info(app_status.status)

    with app_status:
        status_update("Scanning Plugins")

        if not plugins_folder.exists():
            log.error("Could not check plugins because plugins folder is not exist ¯\\_(ツ)_/¯")
            raise FileNotFoundError

        for jar in plugins_folder.glob("*.jar"):
            hash = FileHash(jar)
            name, version, authors = jar_info(jar)
            default_plugin_data = updater_manager.get_plugin_default()

            if plugins_config.get(name, sy.YAML(None, sy.EmptyNone())).data is not None:
                if (
                    hash.md5() == plugins_config[name]["hashes"]["md5"].data
                    and jar.name == plugins_config[name]["file"].data
                ):
                    continue
            else:
                is_new_plugin = True

            # why don't this use recular dict object ?
            # this is because "preserve comments" thing
            # YAML object can hold comments but dict can't
            # and i don't know how tf to add comments directly
            #
            # if the config for plugin is exists then updating will be slow (cuz the validation stuff)
            # otherwise it will be fast
            log.info(f"[green]Update config for {name} [cyan]{jar.name}")
            if not plugins_config.get(name, sy.YAML(None, sy.EmptyNone())).data:
                plugin_data: sy.YAML = default_plugin_data
            else:
                plugin_data = plugins_config[name]

            plugin_data["file"] = jar.name
            plugin_data["version"] = version
            plugin_data["authors"] = authors

            plugin_hashes = plugin_data["hashes"]
            plugin_hashes["md5"] = hash.md5()
            plugin_hashes["sha1"] = hash.sha1()
            plugin_hashes["sha256"] = hash.sha256()
            plugin_hashes["sha512"] = hash.sha512()

            plugins_config[name] = plugin_data

        status_update("Finished scanning plugins")

        if not config.get("settings.keep_removed_plugins", False):
            status_update("Remove deleted plugin")

            _plugins_config: list = deepcopy(list(plugins_config.keys()))
            for name in _plugins_config:
                if not Path(plugins_folder, plugins_config[name]["file"]).exists():
                    log.info(f"[red]Removing {name} from config")
                    del plugins_config[name]
            status_update("Finished removing plugins")

        status_update("Fixing config")
        for plugin_name in list(plugins_config.keys()):
            update_from_default(plugins_config.get(plugin_name), default_plugin_data, plugin_name)
        status_update("Finished fixing config")

        # short the key
        # re-create yaml string
        # parse the yaml string
        # pass to the config
        # this process is much faster thab
        # inserting one by one to the YAML object directly
        status_update("Updating config")
        sorted_key = sorted(plugins_config.keys(), key=lambda k: k.lower())
        _plugins_as_yaml: str = "plugins:\n"
        for i in sorted_key:
            _plugins_as_yaml += reindent(f"{i}:\n", 2)
            for line in plugins_config[i].as_yaml().splitlines():
                if not line.lstrip().startswith("#"):
                    line = re.sub(r"(\s+)#", " #", line)  # remove excessive whitespaces between inline comments
                    line = (" " * 4) + line  # .as_yaml() already dedent the yaml, we only need to add indent
                else:
                    line = reindent(
                        line, 6
                    )  # indent mapping comment, 6 spaces so its in the same level as the subkey of updater
                _plugins_as_yaml += line + "\n"
        data = sy.load(_plugins_as_yaml, sy.Map({"plugins": config.get("plugins").validator}))
        config.set("plugins", data["plugins"])

        config.save()
        config.reload()
        status_update("Config updated")

    if is_new_plugin:
        log.info("[green]You have new plugin, please fill the config")
