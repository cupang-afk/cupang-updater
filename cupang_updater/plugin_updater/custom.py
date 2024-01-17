from typing import Any

import strictyaml as sy

from .base.plugin_updater_base import PluginUpdaterBase


class CustomUpdater(PluginUpdaterBase):
    # Updater information
    name = "Custom Url"
    config_path = "custom_url"
    plugin_config_schema = sy.EmptyNone() | sy.Url()
    plugin_config_default = None

    def __init__(self) -> None:
        super().__init__()
        self.plugin_name = None

        self.url: str = None

    def get_plugin_name(self) -> str:
        # Return the plugin name
        return self.plugin_name

    def get_url(self) -> str:
        # Return the custom URL
        return self.url

    def get_plugin_version(self) -> str | None:
        # Return the plugin version or None if not available
        return None

    def check_update(
        self,
        plugin_name: str,
        plugin_version: str,
        plugin_hash: tuple[str, str, str],
        plugin_config: dict[str, str] | Any,
        updater_config: dict[str, str] | Any | None = None,
    ) -> bool:
        self.plugin_name = plugin_name

        # Set URL from the plugin configuration
        self.url = plugin_config
        if not self.url:
            return False

        # Check the file URL for any issues
        check_file = self.check_file_url(self.url)
        if check_file is not None:
            self.get_log().error(f"When try to check url for {self.plugin_name}, got error: [bold red]{check_file}")
            return False

        return True
