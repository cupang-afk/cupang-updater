import ast
import json
from http import HTTPStatus
from typing import Any

import strictyaml as sy

from ..utils import Date, FileHash
from .base.plugin_updater_base import PluginUpdaterBase


class ModrinthList(sy.Str):
    def is_valid_list(self, s):
        if not s.startswith("[") and not s.endswith("]"):
            return True
        try:
            ast.literal_eval(s)
            return True
        except (SyntaxError, ValueError):
            return False

    def validate_scalar(self, chunk):
        val = chunk.contents
        if not self.is_valid_list(val):
            chunk.expecting_but_found(
                "when expecting string, or a valid list for example \"['paper', 'folia']\","
                " also remember to encapsulate it in quotes"
            )
        return val


class ModrinthUpdater(PluginUpdaterBase):
    # Updater information
    name = "Modrinth"
    config_path = "modrinth"
    plugin_config_schema = sy.Map(
        {
            "id": sy.EmptyNone() | sy.Str(),
            "name_startwith": sy.EmptyNone() | sy.Str(),
            "loaders": sy.EmptyNone() | ModrinthList(),
            "game_versions": sy.EmptyNone() | ModrinthList(),
        }
    )
    plugin_config_default = """
        # id: https://modrinth.com/plugin/[your project id here]
        # name_startwith: file name start with this value, example "Geyser-Spigot"
        # loaders: (optional) example paper, or for many loaders ["paper", "folia"]
        # game_versions: (optional) example 1.20.4, or for many game_versions ["1.20.4", "1.18.2"]
        id:
        name_startwith:
        loaders:
        game_versions:
    """
    api_url = "https://api.modrinth.com/v2"

    def __init__(self) -> None:
        super().__init__()
        self.plugin_name = None
        self.plugin_version = None
        self.plugin_hash = None

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

    def get_update_data(self, project_id: str, loaders: str = None, game_versions: str = None):
        def is_valid_syntax(input: str):
            try:
                # Validate syntax using literal_eval
                output = ast.literal_eval(input)
            except (SyntaxError, ValueError):
                return False
            return output

        def modrinth_params(text: str):
            if text.startswith("[") and text.endswith("]"):
                text = is_valid_syntax(text)
                if text:
                    return "[" + ",".join([f'"{x}"' for x in text]) + "]"
            else:
                return f'["{text}"]'

        # Prepare parameters for the Modrinth API request
        params = {}
        if loaders is not None:
            params["loaders"] = modrinth_params(loaders)
        if game_versions:
            params["game_versions"] = modrinth_params(game_versions)

        # Perform GET request to Modrinth API
        headers = {"Accept": "application/json"}
        res = self.make_requests(
            self.make_url(self.api_url, "project", project_id, "version", **params),
            headers=headers,
            condition=lambda res: HTTPStatus(res.getcode()) == HTTPStatus.OK
            and res.getheader("content-type", "").split(";", 1)[0].lower() == headers["Accept"].lower(),
        )
        if res is None:
            return None

        # Convert the response to a list of release data
        list_release_data: list[dict] = json.loads(res.read())

        # Sort the release data by date_published for release versions
        date_sorted_project_data = {
            Date.from_string(x["date_published"]).utc: x for x in list_release_data if x["version_type"] == "release"
        }

        # Set update_data to the latest release version
        return date_sorted_project_data[max(date_sorted_project_data.keys())]

    def get_file(self, list_files: list[Any], file_key: str, name_startwith: str) -> dict | None:
        file_data = None
        try:
            # Iterate through the list of files and find a match based on name_startwith
            files: list[dict] = list_files
            for file in files:
                filename: str = file[file_key]
                if filename.lower().startswith(name_startwith.lower()):
                    file_data = file
                    break
        except Exception:
            return
        return file_data

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

        project_id = plugin_config.get("id")
        if project_id is None:
            return False

        # Retrieve update data from Modrinth
        release_data = self.get_update_data(
            project_id, plugin_config.get("loaders"), plugin_config.get("game_versions")
        )
        if not release_data:
            return False

        # Compare local and remote versions
        local_version = self.parse_version(plugin_version)
        remote_version = self.parse_version(release_data["version_number"])
        if local_version >= remote_version:
            return False

        # Retrieve file information based on name_startwith
        file = self.get_file(release_data["files"], "filename", plugin_config["name_startwith"])
        if not file:
            return False

        # Set the download URL
        url = file.get("url")
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

        # Update plugin version to the remote version
        self.plugin_version = remote_version
        return True
