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

is_pyinstaller = hasattr(sys, "_MEIPASS") or getattr(sys, "frozen", False)

app_name = "cupang-updater"
if is_pyinstaller:
    app_folder = Path(sys.executable).parent / "cupang-updater"
else:
    app_folder = Path("cupang-updater")
app_folder.mkdir(exist_ok=True)
# app_config
app_config = app_folder / "config.yaml"
# app_ext_updater
app_ext_updater = app_folder / "ext_updater"
app_ext_updater.mkdir(exist_ok=True)

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
