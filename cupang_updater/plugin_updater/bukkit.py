import json
import re
from http import HTTPStatus
from typing import Any

import strictyaml as sy

from ..utils import Date
from ..utils.hash import FileHash
from .base.plugin_updater_base import PluginUpdaterBase


class BukkitUpdater(PluginUpdaterBase):
    # Updater information
    name = "Bukkit"
    config_path = "bukkit"
    plugin_config_schema = sy.Map({"project_id": sy.EmptyNone() | sy.Int()})
    plugin_config_default = """
        # In "About This Project" section in the plugin's page, for example
        # for example 71561 for mythicmobs https://dev.bukkit.org/projects/mythicmobs
        project_id:
    """
    api_url = "https://api.curseforge.com/servermods"
    date_regex = re.compile(r"/Date\((\d+)\)/")

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

    def get_update_data(self, project_id: int) -> dict:
        # Perform a GET request to retrieve update data
        headers = {"Accept": "application/json"}
        res = self.make_requests(
            self.make_url(self.api_url, "files", projectIds=project_id),
            headers=headers,
            condition=lambda res: HTTPStatus(res.getcode()) == HTTPStatus.OK
            and res.getheader("content-type", "").split(";", 1)[0].lower() == headers["Accept"].lower(),
        )
        if res is None:
            return None

        # Convert response to a list of project data
        list_project_data: list[dict] = json.loads(res.read())
        if len(list_project_data) == 0:
            self.get_log().error(f"Failed to parse data for bukkit_id {project_id} because response is empty")
            return None

        # Sort project data by release date
        date_sorted_project_data = {
            Date.from_timestamp(int(self.date_regex.search(x["dateReleased"]).group(1)) / 1000.0).utc: x
            for x in list_project_data
        }

        # Set update_data to the latest release
        return date_sorted_project_data[max(date_sorted_project_data.keys())]

    def check_update(
        self,
        plugin_name: str,
        plugin_version: str,
        plugin_hash: FileHash,
        plugin_config: dict[str, str] | Any,
        updater_config: dict[str, str] | Any | None = None,
    ) -> bool:
        self.plugin_name = plugin_name
        self.plugin_version = plugin_version

        # Check if plugin configuration is available
        if plugin_config.get("project_id") is None:
            return False
        project_id: int = plugin_config.get("project_id")

        # Retrieve update data
        project_data = self.get_update_data(project_id)
        if not project_data:
            return False

        # Compare local and remote MD5 hashes
        local_md5 = plugin_hash.md5()
        remote_md5 = project_data["md5"]
        if local_md5 == remote_md5:
            return False

        # Retrieve download URL
        url = project_data.get("downloadUrl")
        if not url:
            return False
        self.url = url

        # Check the file URL for any issues
        check_file = self.check_head(
            self.url,
            condition=lambda res: res.getheader("content-type", "").lower()
            in ["application/java-archive", "application/octet-stream", "application/zip"],
        )
        if not check_file:
            self.get_log().error(f"When checking update for {self.plugin_name} got url {self.url} but its not a file")
            return False

        # Parse the plugin version from the release data
        self.plugin_version = str(self.parse_version(project_data["name"]))
        return True
