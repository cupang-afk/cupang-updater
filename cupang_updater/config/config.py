from pathlib import Path
from typing import Any

import strictyaml as sy

from ..app.app_config import app_folder
from ..utils import Date, ensure_path
from ..utils.special import ensure_yaml_bool_is_true_false
from .default_config import default_config


class TypeServer(sy.Str):
    server_types = []

    def validate_scalar(self, chunk):
        val = chunk.contents
        if val.lower() not in self.server_types:
            chunk.expecting_but_found(f"when expecting one of {self.server_types}")
        return super().validate_scalar(chunk)

    def update_server_type(self, server_type: str):
        self.server_types.append(server_type)
        # make it unique
        self.server_types = list(sorted(list(set(self.server_types))))


class NonEmptyStr(sy.Str):
    def validate_scalar(self, chunk):
        if chunk.contents == "":
            chunk.expecting_but_found("when expecting some string")
        return chunk.contents


class ConfigSchemaManagerSingleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ConfigSchemaManager(metaclass=ConfigSchemaManagerSingleton):
    def __init__(self):
        ensure_yaml_bool_is_true_false()

        self.settings_schema = {
            "last_update": sy.EmptyNone() | sy.Datetime(),
            "server_folder": sy.Str(),
            "update_cooldown": sy.Int(),
            "keep_removed_plugins": sy.Bool(),
            "update_order": sy.EmptyList() | sy.Seq(sy.Str()),
        }
        self.server_schema = {
            "enable": sy.Bool(),
            "file": sy.Str(),
            "type": TypeServer(),
            "version": NonEmptyStr(),
            "build_number": sy.EmptyNone() | sy.Int(),
            "custom_download_url": sy.EmptyNone() | sy.Url(),
            "hashes": sy.Map(
                {
                    "md5": sy.EmptyNone() | sy.Str(),
                    "sha1": sy.EmptyNone() | sy.Str(),
                    "sha256": sy.EmptyNone() | sy.Str(),
                    "sha512": sy.EmptyNone() | sy.Str(),
                }
            ),
        }

        self.updater_settings_schema = {}
        self.plugin_schema = {
            "exclude": sy.Bool(),
            "file": sy.Str(),
            "version": sy.Str(),
            "authors": sy.EmptyNone() | sy.Seq(sy.Str()),
            "hashes": sy.Map(
                {
                    "md5": sy.EmptyNone() | sy.Str(),
                    "sha1": sy.EmptyNone() | sy.Str(),
                    "sha256": sy.EmptyNone() | sy.Str(),
                    "sha512": sy.EmptyNone() | sy.Str(),
                }
            ),
        }

    def get_server_schema(self) -> dict:
        return self.server_schema

    def get_plugin_schema(self) -> dict:
        return self.plugin_schema

    def get_updater_settings_schema(self) -> dict:
        return self.updater_settings_schema

    def get_schema(self) -> dict:
        config_schema = {
            "settings": sy.Map(self.settings_schema),
            "server": sy.Map(self.server_schema),
            "updater_settings": sy.EmptyDict()
            | sy.MapCombined(
                self.updater_settings_schema,
                sy.Str(),
                sy.EmptyNone() | sy.Any(),
            ),
            "plugins": sy.EmptyDict()
            | sy.MapPattern(
                sy.Str(),
                sy.MapCombined(
                    self.plugin_schema,
                    sy.Str(),
                    sy.EmptyNone() | sy.Any(),
                ),
            ),
        }
        return config_schema


class Config:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = ensure_path(config_path)
        self.config_schema_manager = ConfigSchemaManager()
        self.config = self.__load__()

    @classmethod
    def create_config(cls, config_path: str | Path = None):
        if config_path:
            config_path = ensure_path(config_path)
        else:
            config_path = app_folder / "config.yaml"
        # if config_path.exists():
        #     raise FileExistsError(f"{config_path} is exists")
        config_path.write_text(default_config, encoding="utf-8")
        return cls(config_path)

    def __load__(self):
        config_schema = self.config_schema_manager.get_schema()
        return sy.load(self.config_path.read_text(encoding="utf-8"), sy.Map(config_schema))

    def reload(self):
        self.config = self.__load__()

    def save(self, config_path: str | Path = None):
        if config_path:
            config_path = ensure_path(config_path)
        else:
            config_path = self.config_path
        config_path.write_text(self.config.as_yaml(), encoding="utf-8")

    def set(self, path: str, value: Any):
        """
        Set the value using path.to.value
        """
        if not path:
            return
        if isinstance(value, sy.YAML):
            if not value.data:
                return
        elif not value:
            return
        current = self.config
        paths = path.split(".")
        for k in paths[:-1]:
            if not current.is_mapping() or k not in current:
                break
            current = current[k]
        if paths[-1]:
            current[paths[-1]] = value

    def get(self, path: str, default: Any = None) -> sy.YAML | Any:
        """
        Get the value using path.to.value

        Its recommended to put default as YAML object
        """
        if path == ".":
            return self.config

        # mask default to return sy.YAML object
        if default is None:
            default = sy.YAML(default, sy.EmptyNone())

        current = self.config
        for k in path.split("."):
            if current.is_mapping() and k in current:
                current = current[k]
            else:
                break
        if current.data is None:
            return default
        return current

    def update_updater_settings(self, updater_settings: sy.YAML | dict[str, Any]):
        _data = self.get("updater_settings").data.keys()
        for k, v in updater_settings.items():
            if k in _data:
                continue
            self.set(f"updater_settings.{k}", v)

    def update_update_order(self, order_list: list[str]):
        for i in order_list:
            _data = self.get("settings.update_order").data
            if i in _data:
                continue
            self.set("settings.update_order", _data + [i])

    def update_server_folder(self, path: str):
        _path = ensure_path(path)
        self.set("settings.server_folder", str(_path.expanduser().absolute()))

    def update_last_update(self):
        date = Date.now()
        self.set("settings.last_update", str(date.local))
        # self.set("settings.last_update_local", str(date.local))

    def update_plugin_file(self, name: str, path: str):
        self.set(f"plugins.{name}.file", path)

    def update_plugin_version(self, name: str, version: str):
        self.set(f"plugins.{name}.version", version)

    def update_plugin_hashes(self, name: str, **hashes):
        self.set(f"plugins.{name}.hashes", {**hashes})

    def update_server_type(self, server_types: list[str]):
        """
        Update comments in server.type
        """
        # sort
        server_types.sort()

        server_schema = self.config_schema_manager.get_server_schema()
        st_value: str = self.get("server.type").data
        server_as_yaml: str = self.get("server").as_yaml()
        _server_as_yaml = ""
        for line in server_as_yaml.splitlines():
            if "type:" in line:
                st_index = line.find(st_value)
                line = line[: st_index + len(st_value)].rstrip()
                line += f" # one of these: {', '.join(server_types)}"
            _server_as_yaml += line + "\n"

        new_server_config = sy.load(_server_as_yaml, sy.Map(server_schema))
        self.set("server", new_server_config)
