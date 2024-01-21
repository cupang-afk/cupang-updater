from copy import deepcopy

import strictyaml as sy

from ..config.config import ConfigSchemaManager
from ..logger import LoggerManager
from ..plugin_updater import PluginUpdaterBase
from ..utils import reindent
from ..utils.special import ensure_yaml_bool_is_true_false


class UpdaterManagerSingleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class UpdaterManager(metaclass=UpdaterManagerSingleton):
    def __init__(self) -> None:
        ensure_yaml_bool_is_true_false()

        config_schema_manager = ConfigSchemaManager()
        # dynamicaly filled schema
        self.__updater_settings_schema = config_schema_manager.get_updater_settings_schema()
        self.__plugin_schema = config_schema_manager.get_plugin_schema()
        # set default value
        self.__default: dict[str, sy.YAML] = {
            "plugin": sy.load(
                reindent(
                    """\
                exclude: false # exclude plugin from update checker
                file:
                version:
                authors:
                hashes: # auto generated
                    md5:
                    sha1:
                    sha256:
                    sha512:
                """,
                    6,
                ),
                sy.MapCombined(
                    self.__plugin_schema,
                    sy.Str(),
                    sy.EmptyNone() | sy.Any(),
                ),
            ),
            "updater_settings": sy.as_document({}, sy.EmptyDict() | sy.MapPattern(sy.Str(), sy.EmptyNone() | sy.Any())),
        }

        self.__updaters: dict[str, type[PluginUpdaterBase]] = {}

    def get_updater_settings_default(self) -> sy.YAML:
        data = deepcopy([self.__default["updater_settings"]])[0]
        return data

    def get_plugin_default(self) -> sy.YAML:
        data = deepcopy([self.__default["plugin"]])[0]
        return data

    def get_updater(self, config_path: str) -> type[PluginUpdaterBase] | None:
        return self.__updaters.get(config_path)

    def get_updaters(self) -> dict[str, type[PluginUpdaterBase]]:
        return self.__updaters

    def register(self, cls: PluginUpdaterBase):
        """
        Registers an updater class.

        Parameters:
        - cls: An instance of the PluginUpdaterBase class to register.

        Note: The provided `cls` instance should be initialized before registration.
        """

        log = LoggerManager().get_log()
        log.info(f"Registering updater {cls.name}")
        if not isinstance(cls, PluginUpdaterBase):
            raise ValueError(f"cls should be initialized, and inherit {PluginUpdaterBase.__qualname__}")
        mapping_type = (sy.Map, sy.MapCombined, sy.MapPattern)

        # PLUGIN
        cls_plugin_schema = cls.plugin_config_schema
        cls_plugin_default = cls.plugin_config_default
        cls_config_path = cls.config_path

        # update the schema
        self.__plugin_schema[sy.Optional(cls_config_path)] = cls_plugin_schema
        # re-set the schema
        self.__default["plugin"]._validator = sy.Map(
            self.__plugin_schema,
        )

        # set default value
        if isinstance(cls_plugin_default, str) and isinstance(cls_plugin_schema, mapping_type):
            # create indent
            default_value = reindent(cls_plugin_default, 2)

            yaml = sy.load(default_value, cls_plugin_schema)
            self.__default["plugin"][cls_config_path] = yaml
        else:
            self.__default["plugin"][cls_config_path] = cls_plugin_default

        # UPDATER
        cls_updater_schema = cls.updater_config_schema
        cls_updater_default = cls.updater_config_default

        if cls_updater_schema is not None:
            # update the schema
            self.__updater_settings_schema[sy.Optional(cls_config_path)] = cls_updater_schema
            # re-set the schema
            self.__default["updater_settings"]._validator = sy.Map(self.__updater_settings_schema)

            # set default value
            if isinstance(cls_updater_default, str) and isinstance(cls_updater_schema, mapping_type):
                yaml = sy.load(cls_updater_default, cls_updater_schema)
                self.__default["updater_settings"][cls_config_path] = yaml.data
            else:
                self.__default["updater_settings"][cls_config_path] = cls_updater_default

        self.__updaters[cls.config_path] = type(cls)
