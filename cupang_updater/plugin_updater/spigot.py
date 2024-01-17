import json
from http import HTTPStatus
from http.client import HTTPResponse
from typing import Any

import strictyaml as sy

from ..utils import FileHash
from .base.plugin_updater_base import PluginUpdaterBase


class SpigotUpdater(PluginUpdaterBase):
    # Updater information
    name = "Spigot"
    config_path = "spigot"
    plugin_config_schema = sy.Map({"resource_id": sy.EmptyNone() | sy.Int()})
    plugin_config_default = """
        # In spigotmc url
        # for example: 18494 for discordsrv https://www.spigotmc.org/resources/discordsrv.18494/
        resource_id:
    """
    api_url = "https://api.spiget.org/v2"

    def __init__(self) -> None:
        super().__init__()
        self.plugin_name = None
        self.plugin_version = None

        self.url: str = None

    def get_plugin_name(self) -> str:
        # Return the plugin name
        return self.plugin_name

    def get_url(self) -> str:
        # Return the download URL
        return self.url

    def get_plugin_version(self) -> str | None:
        # Return the plugin version or None if not available
        return self.plugin_version

    def get_update_data(self, resource_id: int) -> tuple[dict, dict]:
        # Perform GET requests to Spiget API for resource data and latest version
        headers = {"Accept": "application/json"}
        resource_data = self.make_requests(
            self.make_url(self.api_url, "resources", resource_id),
            headers=headers,
        )
        resource_latest = self.make_requests(
            self.make_url(self.api_url, "resources", resource_id, "versions", "latest"),
            headers=headers,
        )

        # Check the response for errors
        resource_data = self.check_response(resource_data, headers)
        resource_latest = self.check_response(resource_latest, headers)
        if resource_data is None or resource_latest is None:
            return None

        # Convert the response data to dictionaries
        resource_data = json.loads(resource_data.read())
        resource_latest = json.loads(resource_latest.read())

        return resource_data, resource_latest

    def check_response(self, res: HTTPResponse | None, headers: dict) -> HTTPResponse | None:
        # Check the HTTP response for errors and return the response or None
        if res is None:
            self.get_log().error(f"Failed to fetch data for {self.plugin_name} because response is empty")
            return

        res_code = HTTPStatus(res.getcode())
        if res_code != HTTPStatus.OK:
            self.get_log().error(
                f"Failed to fetch data for {self.plugin_name} " f"because {res_code.value} {res_code.phrase}"
            )
            return

        content_type = res.getheader("content-type")
        if content_type is None:
            self.get_log().error(f"Requesting {headers['Accept']} for {self.plugin_name} but got None")
            return

        # Check if the content type matches the expected value
        if headers["Accept"] not in content_type.split(";"):
            self.get_log().error(f"Requesting {headers['Accept']} for {self.plugin_name} " f"but got {content_type}")
            return
        return res

    def check_update(
        self,
        plugin_name: str,
        plugin_version: str,
        plugin_hash: FileHash,
        plugin_config: dict[str, str] | Any,
        updater_config: dict[str, str] | Any | None = None,
    ) -> bool:
        # Set plugin data
        self.plugin_name = plugin_name
        self.plugin_version = plugin_version

        # Set resource_id
        resource_id = plugin_config.get("resource_id")
        if resource_id is None:
            return False
        # Retrieve update data from Spiget API
        data = self.get_update_data(resource_id)
        if not data:
            return False
        resource_data, resource_latest = data
        if not resource_data or not resource_latest:
            return False

        # Compare local and remote versions
        local_version = self.parse_version(plugin_version)
        remote_version = self.parse_version(resource_latest["name"])
        if local_version >= remote_version:
            return False

        # Check if the plugin is marked as premium
        if resource_data["premium"]:
            self.get_log().info(
                f"Plugin {self.plugin_name} is premium\n"
                f"Download it yourself at https://www.spigotmc.org/resources/{resource_id}"
            )
            return False

        # Set the download URL
        url = self.make_url(self.api_url, "resources", resource_id, "download")
        if not url:
            return False
        self.url = url

        # Check the file URL for any issues
        check_file = self.check_file_url(self.url)
        if check_file is not None:
            self.get_log().error(f"When try to check url for {self.plugin_name}, got error: [bold red]{check_file}")
            return False

        # Update plugin version to the remote version
        self.plugin_version = str(remote_version)
        return True
