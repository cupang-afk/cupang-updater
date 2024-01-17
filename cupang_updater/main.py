from pathlib import Path

from rich.prompt import Prompt

from .app.app_config import app_config, app_console, app_ext_updater, app_stop_event
from .cmd import args
from .config import Config
from .logger import LoggerManager
from .manager import ExtManager, ServerUpdaterManager, UpdaterManager
from .plugin_updater import (
    BukkitUpdater,
    CustomUpdater,
    GithubUpdater,
    JenkinsUpdater,
    ModrinthUpdater,
    SpigotUpdater,
)
from .server_updater import PaperUpdater, ServerjarsUpdater
from .task.scan import scan_plugins
from .task.update import update_plugins


def main():
    try:
        log = LoggerManager().get_log()
        s = ServerUpdaterManager()
        u = UpdaterManager()
        e = ExtManager()

        s.register(ServerjarsUpdater())
        s.register(PaperUpdater())
        for i in [
            CustomUpdater,
            BukkitUpdater,
            SpigotUpdater,
            ModrinthUpdater,
            GithubUpdater,
            JenkinsUpdater,
        ]:
            u.register(i())

        e.register(app_ext_updater)
        # if args.ext_updater:
        #     e.register(app_ext_updater, *args.ext_updater)
        # else:
        #     e.register(app_ext_updater)
        log.info("Loading config")
        if not app_config.exists():
            c = Config.create_config(app_config)
        else:
            c = Config(app_config)
        if not c.get("settings.server_folder").data:
            while True:
                server_folder = Prompt.ask(
                    "Enter server folder, must be a full path (i.e. /root/minecraft)", console=app_console
                )
                server_folder = Path(server_folder)
                if server_folder.is_absolute():
                    c.update_server_folder(server_folder)
                    break
                log.error("Must be a full path (i.e. /root/minecraft)")
        # c.update_server_folder("E:\\RECODED_UPDATER_2\\test__")
        c.update_server_type([x for types in list(s.get_updaters().values()) for x in types])
        c.update_update_order(list(u.get_updaters().keys()))
        c.update_updater_settings(u.get_updater_settings_default())

        # exit()

        if args.scan_only:
            scan_plugins(c)
            exit()
        else:
            scan_plugins(c)
            update_plugins(c)
    except KeyboardInterrupt:
        app_stop_event.set()


if __name__ == "__main__":
    main()