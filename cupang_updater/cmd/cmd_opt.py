import importlib.metadata
import sys
from argparse import ArgumentParser
from pathlib import Path

is_pyinstaller = hasattr(sys, "_MEIPASS") or getattr(sys, "frozen", False)
opt = ArgumentParser(Path(sys.executable).name if is_pyinstaller else Path(sys.argv[0]).name)

opt.add_argument(
    "--version",
    action="version",
    version="%(prog)s {version}".format(version=importlib.metadata.version("cupang-updater")),
)
opt_main_usage = opt.add_argument_group("Main Options")
opt_main_usage.add_argument(
    "-f",
    "--force",
    dest="force",
    action="store_true",
    default=False,
    help="Force to do update check despite the cooldown (default: %(default)s)",
)
opt_main_usage.add_argument(
    "--scan-only",
    dest="scan_only",
    action="store_true",
    default=False,
    help="Scan plugins without checking update (default: %(default)s)",
)
opt_main_usage.add_argument(
    "--config-dir",
    dest="config_dir",
    action="store",
    metavar="PATH",
    type=Path,
    help="Set config dir (default: cupang-updater)",
)
opt_main_usage.add_argument(
    "--config",
    dest="config_path",
    action="store",
    metavar="PATH",
    help="Set config.yaml path relative to the --config-dir unless full path is given (default: config.yaml)",
)

opt_config_usage = opt.add_argument_group("config options")
opt_config_usage.add_argument(
    "--config-cleanup",
    dest="config_cleanup",
    action="store_true",
    default=True,
    help="Cleanup your config from unregistered updater (default: %(default)s)",
)

# opt_ext_usage = opt.add_argument_group("ext updater options")
# opt_ext_usage.add_argument(
#     "--ext-updater",
#     dest="ext_updater",
#     action="append",
#     type=Path,
#     metavar="PATH",
#     help="Add ext_updater folder to be registered",
# )

args = opt.parse_args()
