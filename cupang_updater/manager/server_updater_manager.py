from ..config.config import ConfigSchemaManager
from ..logger.logger import LoggerManager
from ..server_updater import ServerUpdaterBase
from ..utils.special import ensure_yaml_bool_is_true_false


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

    def get_supported_type(self) -> list[str]:
        """get list of server type supported by the registered updater

        Returns:
            list[str]
        """
        result = list(x for y in self.__updaters.values() for x in y)
        result = list(set(result))
        result.sort()
        return result

    def get_updaters(self, server_type: str) -> list[type[ServerUpdaterBase]]:
        """get the list of updater that support the `server_type`

        Args:
            server_type (str): the type of the server e.g, paper, purpur, bungeecord, etc

        Returns:
            list[type[ServerUpdaterBase]]
        """
        result = list(map(lambda i: i[0] if server_type in i[1] else None, self.__updaters.items()))
        result = list(filter(lambda i: i is not None, result))
        return result

    def register(self, cls: ServerUpdaterBase):
        """_summary_

        Args:
            cls (ServerUpdaterBase): An instance of the ServerUpdaterBase class to register

        Raises:
            ValueError: cls should inherit `ServerUpdaterBase` and initialized
        """

        log = LoggerManager().get_log()
        log.info(f"Registering server updater {cls.name}")
        if not isinstance(cls, ServerUpdaterBase):
            raise ValueError(f"cls should inherit {ServerUpdaterBase.__qualname__}")

        for server_type in cls.server_type_list:
            self.__server_schema["type"].update_server_type(
                server_type
            )  # guaranteed to be TypeServer scalar, look at ConfigSchemaManager

        self.__updaters[type(cls)] = cls.server_type_list
