import sys
from importlib.util import module_from_spec, spec_from_file_location
from itertools import chain
from pathlib import Path

from ..logger import LoggerManager
from ..utils import ensure_path


class ExtManagerSingleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ExtManager(metaclass=ExtManagerSingleton):
    def __init__(self) -> None:
        self.__registered = False

    def __load_ext(self, name: str, path: Path):
        path = ensure_path(path)
        spec = spec_from_file_location(name, path.absolute())
        module = module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)

    def register(self, *ext_paths: Path | str):
        log = LoggerManager().get_log()
        if self.__registered:
            log.error("Ext already registered")
            return
        for item in chain.from_iterable(path.glob("*") for path in ext_paths):
            try:
                if item.is_dir():
                    main_py = item / "main.py"
                    if main_py.exists():
                        sys.path.append(str(item.absolute()))
                        self.__load_ext(item.name, main_py.absolute())
                elif item.suffix == ".py":
                    self.__load_ext(item.stem, item.absolute())
            except Exception:
                log.exception(f"Exception occur when trying to register {item}")
        self.__registered = True
