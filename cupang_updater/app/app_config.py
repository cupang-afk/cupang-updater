import importlib.metadata
import importlib.util
import sys
from functools import partial
from pathlib import Path
from threading import Event

import rich.console
import rich.live
import rich.progress
import rich.status
import rich.traceback

from ..cmd import args

is_pyinstaller = hasattr(sys, "_MEIPASS") or getattr(sys, "frozen", False)

app_name = "cupang-updater"
app_version = importlib.metadata.version(app_name)
# app_folder
if is_pyinstaller:
    app_folder = Path(sys.executable).parent
else:
    app_folder = Path()
if args.config_dir:
    app_folder: Path = args.config_dir
else:
    app_folder = app_folder / "cupang-updater"
app_folder.mkdir(exist_ok=True)
# app_config
app_config = app_folder / "config.yaml"
if args.config_path:
    _app_config = Path(args.config_path)
    if not _app_config.is_absolute():
        app_config = app_folder / _app_config
    else:
        app_config = _app_config
# app_ext_updater
app_ext_updater = app_folder / "ext_updater"

log_folder = app_folder / "logs"
log_folder.mkdir(exist_ok=True)
cache_folder = app_folder / "cache"
cache_folder.mkdir(exist_ok=True)

app_headers = {"User-Agent": "Cupang-Updater/0.1.0"}
app_has_pycurl = importlib.util.find_spec("pycurl")
app_stop_event = Event()

app_console = rich.console.Console(tab_size=4)
app_progress = rich.progress.Progress(
    rich.progress.TextColumn("[bold blue]{task.description}"),
    rich.progress.BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    rich.progress.DownloadColumn(),
    "•",
    rich.progress.TransferSpeedColumn(),
    "•",
    rich.progress.TimeRemainingColumn(),
    console=app_console,
    transient=True,
)
app_status = rich.status.Status("...", console=app_console)
app_live = partial(rich.live.Live, console=app_console, transient=True)


rich.traceback.install(console=app_console)
