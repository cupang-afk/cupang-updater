import logging
import zipfile
from datetime import datetime

from rich.console import Console
from rich.logging import RichHandler

from ..app.app_config import app_console


class CustomLogFormatting(logging.Formatter):
    def format(self, record):
        names = record.name.split(".") if record.name else []
        # # remove name
        # if names:
        #     try:
        #         names.pop(names.index(app_name))
        #     except (IndexError, ValueError):
        #         pass
        match record.levelno:
            case logging.WARNING:
                record.msg = f"[red]{record.msg}"
            case logging.ERROR:
                record.msg = f"[bold red]{record.msg}"
            case logging.CRITICAL:
                record.msg = f"[bold black on red]{record.msg}"
            case _:
                record.msg = f"[default on default]{record.msg}"
        if len(names) >= 1:
            main_name, *names = names
            if names:
                record.msg = f"[bright_blue][{' '.join(names)}] {record.msg}"
            # if names:
            #     record.msg = f"[bright_cyan]\[{main_name}] [bright_blue]\[{' '.join(names)}]: {record.msg}"  # noqa
            # else:
            #     record.msg = f"[bright_cyan]\[{main_name}]: {record.msg}"  # noqa
        return super().format(record)


class LoggerManagerSingleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class LoggerManager(metaclass=LoggerManagerSingleton):
    def __init__(self):
        from cupang_updater.app.app_config import log_folder

        self.__today = datetime.now().date()
        self.__name_format = "console_*_*.log"
        self.date_format = "%Y-%m-%d"
        self.log_folder = log_folder
        self.latest_log = log_folder / "latest.log"
        self.log = None

    def get_log(self) -> logging.Logger:
        if self.log is None:
            self.__setup_log()
            self.__compress_log()
        return self.log

    def __setup_log(self):
        self.__rename_log()

        log = logging.getLogger("Updater")
        log.setLevel(logging.DEBUG)

        log_formatter = CustomLogFormatting("%(message)s", datefmt="%X")

        log_handler = RichHandler(
            console=app_console,
            rich_tracebacks=True,
            markup=True,
            show_path=False,
        )
        file_handler = RichHandler(
            console=Console(
                file=self.latest_log.open("a", encoding="utf-8"),
                tab_size=app_console.tab_size,
            ),
            rich_tracebacks=True,
            markup=True,
        )

        log_handler.setLevel(logging.INFO)
        file_handler.setLevel(logging.DEBUG)
        log_handler.setFormatter(log_formatter)
        file_handler.setFormatter(log_formatter)

        log.addHandler(log_handler)
        log.addHandler(file_handler)

        log.info(f"Logger created at {self.__today.strftime(self.date_format)}")

        self.log = log

    def __get_latest_exec_n(self):
        exec_n = [int(log.stem.split("_")[-1]) for log in self.log_folder.glob(self.__name_format)]
        return max(exec_n, default=0) + 1

    def __rename_log(self):
        _latest_log = self.latest_log
        if _latest_log.is_file():
            date_formatted = self.__today.strftime(self.date_format)
            exec_n = self.__get_latest_exec_n()
            new_name = f"console_{date_formatted}_{exec_n}.log"
            _latest_log.rename(self.log_folder / new_name)

    def __compress_log(self):
        date_formatted = self.__today.strftime(self.date_format)
        for log_file in self.log_folder.glob(self.__name_format):
            _, log_date, _ = log_file.stem.split("_")
            log_file_date = datetime.strptime(log_date, self.date_format).date()
            if log_file_date >= self.__today:
                continue
            with zipfile.ZipFile(
                self.log_folder / f"{date_formatted}.zip",
                mode="a",
                compression=zipfile.ZIP_BZIP2,
                compresslevel=9,
            ) as z:
                z.write(log_file, log_file.name)
            log_file.unlink()


# initialize
LoggerManager()
