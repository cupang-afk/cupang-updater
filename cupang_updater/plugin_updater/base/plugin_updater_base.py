from abc import abstractmethod
from typing import Any

from strictyaml import ScalarValidator

from ...base_class import UpdaterBase
from ...utils.hash import FileHash


class PluginUpdaterBase(UpdaterBase):
    """Abstract base class for updater plugins.

    Important: Set these class variables when creating a class

    ```python
    # Example CustomUpdater
    import strictyaml as sy


    class CustomUpdater(PluginUpdaterBase):
        name = "Custom Url Updater"
        config_path = "custom_url"
        plugin_config_schema = sy.Url()
        plugin_config_default = None
    ```

    Class variables that need to be set:

    - `name`: The updater name (set when creating the class).
    - `config_path`: Name in the config, lowercase, underscores, and no hyphens are recommended.
    - `plugin_config_schema`: Configuration schema for each plugin. Must be a strictyaml schema.
    - `plugin_config_default`: Default value for plugin config. If `plugin_config_schema` is a mapping type, use YAML string format.
    - `updater_config_schema` (optional): YAML schema for the updater's configuration. Must be a strictyaml schema.
    - `updater_config_default` (if `updater_config_schema` is set): Default value for the updater's configuration. If `updater_config_schema` is a mapping type, use YAML string format.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The updater name.
        """
        ...

    @property
    @abstractmethod
    def config_path(self) -> str:
        """No whitespace allowed. Lowercase is recommended."""
        ...

    @property
    @abstractmethod
    def plugin_config_schema(self) -> ScalarValidator:
        """
        YAML schema for the plugin's configuration.

        This schema will be used in each plugin's configuration file
        and can include fields like `bukkit_id`, `spigot_id`, etc.

        Must be a strictyaml schema.
        """
        ...

    @property
    @abstractmethod
    def plugin_config_default(self) -> Any:
        """
        Default value for the plugin's configuration.

        Note: If `plugin_config_schema` is a mapping type, this should be YAML string format.
        """
        ...

    @property
    def updater_config_schema(self) -> ScalarValidator:
        """
        YAML schema for the updater's configuration (optional).

        This schema will be placed under the `updater_settings` section
        in the main config.yaml file. It can include global settings
        such as OAuth keys.

        Must be a strictyaml schema.
        """
        ...

    @property
    def updater_config_default(self) -> Any:
        """
        Default value for the updater's configuration
            (should be present if `updater_config_schema` is set).

        Note: If `updater_config_schema` is a mapping type, this should be YAML string format.
        """
        ...

    @abstractmethod
    def check_update(
        self,
        plugin_name: str,
        plugin_version: str,
        plugin_hash: FileHash,
        plugin_config: dict[str, str] | Any,
        updater_config: dict[str, str] | Any | None = None,
    ) -> bool:
        """Main function for checking updates.

        Determines whether an update is available.

        It's recommended to check `plugin_config` before proceeding further.

        Return True if an update is available, otherwise False.

        Should never raise any exception
        """
        ...

    @abstractmethod
    def get_plugin_name(self) -> str:
        """
        Return the name of the plugin.
        """
        ...

    @abstractmethod
    def get_plugin_version(self) -> str | None:
        """
        Return the plugin version.

        If an update is available, return the updated version.
        For example, if the current version is 1.0 and a new version is detected,
        return the new version, i.e., 2.0.

        If the version cannot be obtained from the update site,
        return None to use the version from the .jar file.
        """
        ...

    def get_plugin_config_updates(self) -> list[tuple[str, Any]]:
        """
        Note: Set this when you want to update your `plugin_config`

        Update the plugin configuration.

        Returns a list of tuples in the format (key, value) to update the plugin configuration.
        The key is relative to your `plugin_config`.

        If the `plugin_config` is not using `strictyaml.Map()` or any similar structure,
        use `.` as the key.

        ```python
            # Example return
            update_config = [
                ("build_number", 123),
                ("commit", "aabbcc"),
                ("example.nested.key", True),
                (".", True)
            ]
            return update_config
        ```
        """
        ...

    def get_updater_config_updates(self) -> list[tuple[str, Any]]:
        """
        Note: Set this when you want to update your `updater config`

        Update the updater configuration.

        Returns a list of tuples in the format (key, value) to update the updater configuration.
        The key is relative to your `updater_config`.

        If the `updater_config` is not using `strictyaml.Map()` or any similar structure,
        use `.` as the key.

        ```python
            # Example return:
            update_config = [
                ("oauth", auth_key)
            ]
            return update_config
        ```
        """
        ...
