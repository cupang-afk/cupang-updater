import shutil
import time
from copy import deepcopy
from datetime import timedelta
from multiprocessing import ProcessError
from multiprocessing.pool import ApplyResult, ThreadPool
from pathlib import Path
from typing import Any

import strictyaml as sy
from rich.console import Group

from ..app.app_config import app_live, app_progress, app_status, app_stop_event, args
from ..checker.plugin_checker import jar_info
from ..config import Config
from ..downloader import download
from ..logger import LoggerManager
from ..manager.server_updater_manager import ServerUpdaterManager
from ..manager.updater_manager import UpdaterManager
from ..plugin_updater import PluginUpdaterBase
from ..server_updater import ServerUpdaterBase
from ..utils import Date
from ..utils.hash import FileHash

log = LoggerManager().get_log()


def update_plugins(config: Config):
    last_update = config.get("settings.last_update").data
    if last_update and not args.force:
        today = Date.now()
        last_update = Date(last_update)
        cooldown = timedelta(hours=config.get("settings.update_cooldown", sy.YAML(12, sy.Int())).data)

        # Check time elapsed since the last update
        if (today.local - last_update.local) <= cooldown:
            # Calculate the remaining time
            remaining = (last_update.local + cooldown) - today.local
            log.info(f"Updater still in cooldown, {round(remaining.total_seconds() / 3600)} hours remaining")
            return

    def status_update(msg: str, log_type: str = "info", no_log: bool = False):
        app_status.update(msg)
        if not no_log:
            match log_type.lower():
                case "error":
                    log.error(app_status.status)
                case "warning":
                    log.warning(app_status.status)
                case "debug":
                    log.debug(app_status.status)
                case _:
                    log.info(app_status.status)

    with app_live(Group(app_progress, app_status)):
        app_status.update("...")

        server_folder = Path(config.get("settings.server_folder").data)
        if config.get("server.enable", True):
            status_update("Updating server")

            server_file = server_folder / str(config.get("server.file").data)

            # calculate hashes
            # if not exists, set placeholder
            if server_file.exists():
                hash = FileHash(server_file)
                hashes = {
                    "md5": hash.md5(),
                    "sha1": hash.sha1(),
                    "sha256": hash.sha1(),
                    "sha512": hash.sha512(),
                }
                config.set("server.hashes", hashes)
            else:
                config.set("server.hashes", {"md5": "a", "sha1": "b", "sha256": "c", "sha512": "d"})

            server_type = config.get("server.type").data
            server_version = config.get("server.version").data
            server_build_number = config.get("server.build_number").data
            server_hashes = FileHash.with_known_hashes(server_folder / server_file, config.get("server.hashes").data)
            server_updater_manager = ServerUpdaterManager()

            server_updater_list: list[type[ServerUpdaterBase]] = server_updater_manager.get_updater(server_type)
            for updater in server_updater_list:
                updater = updater()

                if updater.check_update(
                    server_type,
                    server_version,
                    server_hashes,
                    server_build_number,
                ):
                    status_update(f"Updating {server_type} {server_version}", no_log=True)
                    new_file = download(updater.get_url(), server_file.name, updater.get_headers())
                    if new_file is None:
                        log.error(f"Trying another server updater for {server_type}")
                        continue
                    config.set("server.build_number", updater.get_build_number())
                    config.set("server.hashes.md5", FileHash(new_file).md5())
                    shutil.move(new_file.absolute(), (server_folder / server_file).absolute())
                    break

            status_update("Finished updating server")

        status_update("Prepare updating plugins")
        plugins_folder = server_folder / "plugins"
        if not plugins_folder.exists():
            log.error(f"I don't know how you do it, but your {plugins_folder} is missing for some reason")
            return 1

        updater_manager = UpdaterManager()
        updater_settings = config.get("updater_settings").data
        log.info("Get updater order")
        updater_list: list[type[PluginUpdaterBase]] = []
        for i in config.get("settings.update_order", sy.YAML([], sy.EmptyList())).data:
            if app_stop_event.is_set():
                break
            updater = updater_manager.get_updater(i)

            # TODO: make this check happen at register
            if updater is None:
                log.error(f"Updater {i} is not registered")
                continue

            updater_list.append(updater)

        plugins: dict[str, dict[str, Any]] = deepcopy(dict(config.get("plugins").data))
        updated_plugins: dict[str, dict[str, Any]] = {}

        workers = ThreadPool(5)
        worker_jobs: list[ApplyResult] = []

        def update_helper(
            updater_list: list[type[PluginUpdaterBase]],
            plugin_name: str,
            plugin_data: dict,
            updated_plugins: dict[str, dict[str, Any]],
            old_file: Path,
        ):
            for updater in updater_list:
                # initialize updater
                updater = updater()
                plugin_config = deepcopy([plugin_data[updater.config_path]])[0]
                updater_config = deepcopy([updater_settings.get(updater.config_path)])[0]
                if updater.check_update(
                    plugin_name,
                    plugin_data["version"],
                    FileHash.with_known_hashes(old_file, plugin_data["hashes"]),
                    plugin_config,
                    updater_config,
                ):
                    try:
                        new_version = updater.get_plugin_version()
                        new_file_name = f"{updater.get_plugin_name()} [{updater.name}]"

                        new_file = download(
                            updater.get_url(),
                            new_file_name + f" [{new_version or 'Latest'}].jar",
                            updater.get_headers(),
                        )
                        if new_file is None:
                            log.error(f"Trying another plugin updater for {updater.get_plugin_name()}")
                            continue

                        if new_version is None:
                            _, new_version, _ = jar_info(new_file)
                        new_file_name = new_file_name + f" [{new_version}].jar"
                        new_file_hash = FileHash(new_file)

                        updated_plugins[updater.get_plugin_name()] = {
                            "file": new_file_name,
                            "version": str(new_version),
                            "hashes": {
                                "md5": new_file_hash.md5(),
                                "sha1": new_file_hash.sha1(),
                                "sha256": new_file_hash.sha1(),
                                "sha512": new_file_hash.sha512(),
                            },
                            "update_config": {
                                "path": f"{plugin_name}.{updater.config_path}",
                                "plugin_config": updater.get_plugin_config_updates(),
                                "updater_config": updater.get_updater_config_updates(),
                            },
                        }

                        old_file.unlink(missing_ok=True)
                        shutil.move(new_file.absolute(), (plugins_folder / new_file_name).absolute())
                        break
                    except Exception as e:
                        log.error(
                            f"When trying to update {updater.get_plugin_name()} using {updater.name}\n"
                            f"got error: [bold red]{e}"
                        )

        status_update("Adding update bobs")
        for plugin_name, plugin_data in plugins.items():
            status_update(f"Adding job for {plugin_name}", "debug")

            # get old file
            old_file = plugins_folder / str(plugin_data.get("file", ".unknown"))

            # skip excluded
            # also checking old_file existence to fulfill keep_removed_plugin behaviour
            if plugin_data.get("exclude", True):
                log.info(f"Excluding {plugin_name}")
                return
            if not old_file.exists():
                log.info(f"Skipping {plugin_name}, because its a leftover")
                return

            # add download job
            worker_jobs.append(
                workers.apply_async(
                    update_helper,
                    (
                        updater_list,
                        plugin_name,
                        plugin_data,
                        updated_plugins,
                        old_file,
                    ),
                )
            )
            # update_helper(
            #     updater_list,
            #     plugin_name,
            #     plugin_data,
            #     updated_plugins,
            #     old_file,
            # )

        status_update("Jobs added, waiting for completion")
        try:
            while not all([x.ready() for x in worker_jobs]):
                time.sleep(1)
        except (KeyboardInterrupt, ProcessError, Exception):
            app_stop_event.set()
        finally:
            workers.close()
            workers.join()

        def update_config(config_data):
            for k, v in config_data:
                config.set(f"plugins.{update_config_path}.{k.strip('.')}", v)

        for plugin_name, new_plugin_data in updated_plugins.items():
            status_update(f'[green]Update config for {plugin_name} {new_plugin_data["file"]}')
            config.update_plugin_file(plugin_name, new_plugin_data["file"])
            config.update_plugin_version(plugin_name, new_plugin_data["version"])
            config.update_plugin_hashes(plugin_name, **new_plugin_data["hashes"])

            update_config_path = new_plugin_data["update_config"]["path"]
            update_plugin_config = new_plugin_data["update_config"]["plugin_config"]
            update_updater_config = new_plugin_data["update_config"]["updater_config"]

            if update_plugin_config:
                update_config(update_plugin_config)

            if update_updater_config:
                update_config(update_updater_config)

        config.update_last_update()
        config.save()
        config.reload()
        status_update("Finished updating plugins")
