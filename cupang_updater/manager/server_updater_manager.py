from ..config.config import ConfigSchemaManager
from ..logger.logger import LoggerManager
from ..server_updater import ServerUpdaterBase
from ..utils.special import ensure_yaml_bool_is_true_false

log = LoggerManager().get_log()


class ServerUpdaterManagerSingleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ServerUpdaterManager(metaclass=ServerUpdaterManagerSingleton):
    def __init__(self) -> None:
        ensure_yaml_bool_is_true_false()

        config_schema_manager = ConfigSchemaManager()
        self.__server_schema = config_schema_manager.get_server_schema()

        self.__updaters: dict[type[ServerUpdaterBase], list[str]] = {}

    def get_updater(self, server_type: str) -> list[type[ServerUpdaterBase]]:
        result = []
        for k, v in self.__updaters.items():
            if server_type in v:
                result.append(k)
        return result

    def get_updaters(self) -> dict[type[ServerUpdaterBase], list[str]]:
        """
        Returns the updater as the key, and supporter server_type as the value
        """
        return self.__updaters

    def register(self, cls: ServerUpdaterBase):
        """
        Registers an updater class.

        Parameters:
        - cls: An instance of the ServerUpdaterBase class to register.

        Note: The provided `cls` instance should be initialized before registration.
        """

        log.info(f"Registering server updater {cls.name}")
        if not isinstance(cls, ServerUpdaterBase):
            raise ValueError(f"cls should inherit {ServerUpdaterBase.__qualname__}")

        for server_type in cls.server_type_list:
            self.__server_schema["type"].update_server_type(
                server_type
            )  # guaranteed to be TypeServer scalar, look at ConfigSchemaManager

        self.__updaters[type(cls)] = cls.server_type_list
