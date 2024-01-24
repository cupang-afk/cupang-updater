import json
from http import HTTPStatus
from typing import Any

import strictyaml as sy

from ..utils import FileHash
from .base.plugin_updater_base import PluginUpdaterBase


class CompareToType(sy.Str):
    compare_to = ["commit", "tags", "release_name", "file_name"]

    def validate_scalar(self, chunk):
        val = chunk.contents
        if val.lower() not in self.compare_to:
            chunk.expecting_but_found(f"when expecting one of {self.compare_to}")
        return val


class GithubUpdater(PluginUpdaterBase):
    # Updater information
    name = "Github"
    config_path = "github"
    plugin_config_schema = sy.Map(
        {
            "repo": sy.EmptyNone() | sy.Str(),
            "name_startwith": sy.EmptyNone() | sy.Str(),
            "commit": sy.EmptyNone() | sy.Str(),
            "compare_to": CompareToType(),
        }
    )
    plugin_config_default = """
        # repo: format is user/repository for example EssentialsX/Essentials
        # name_startwith: file name start with this value, example "Geyser-Spigot"
        # compare_to: one of these: commit, tags, release_name, file_name
        repo:
        name_startwith:
        commit:
        compare_to: commit
    """
    updater_config_schema = sy.Map({"github_token": sy.EmptyNone() | sy.Str()})
    updater_config_default = """
        github_token:
    """
    api_url = "https://api.github.com"

    def __init__(self) -> None:
        super().__init__()
        self.plugin_name = None
        self.plugin_version = None

        self.token: str = None
        self.commit: str = None
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

    def get_plugin_config_updates(self) -> list[tuple[str, Any]]:
        updates = [("commit", self.commit)]
        return updates

    def get_headers(self) -> dict[str, Any]:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}

    def get_update_data(self, repo: str) -> dict:
        # Perform GET request for release data
        headers = {"Accept": "application/json"}
        if self.token:
            headers.update(self.get_headers())
        res_release = self.make_requests(
            self.make_url(self.api_url, "repos", repo, "releases", "latest"),
            headers=headers,
            condition=lambda res: HTTPStatus(res.getcode()) == HTTPStatus.OK
            and res.getheader("content-type", "").split(";", 1)[0].lower() == headers["Accept"].lower(),
        )
        if res_release is None:
            return None
        release_data = json.loads(res_release.read())

        # Perform GET request for tag data
        res_tag = self.make_requests(
            self.make_url(
                self.api_url,
                "repos",
                repo,
                "git",
                "ref",
                "tags",
                release_data["tag_name"],
            ),
            headers=headers,
        )
        if res_tag is None:
            return None
        tag_data = json.loads(res_tag.read())

        return release_data, tag_data

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

        self.token = updater_config["github_token"]

        # Extract repository information from plugin configuration
        repo = plugin_config.get("repo")
        if repo is None:
            return False

        # Extract name_startwith from plugin configuration
        name_startwith = plugin_config.get("name_startwith")
        if name_startwith is None:
            return False

        # Retrieve release and tag data
        data = self.get_update_data(repo)
        if not data:
            return False
        release_data, tag_data = data

        # Check update based on the specified compare_to type
        compare_to = plugin_config["compare_to"].lower()

        local_commit = plugin_config.get("commit")
        remote_commit = tag_data["object"]["sha"]

        local_version = self.parse_version(self.get_plugin_version())
        match compare_to:
            case "tags":
                remote_version = self.parse_version(release_data["tag_name"])
            case "release_name":
                remote_version = self.parse_version(release_data["name"])
            case "file_name":
                remote_version = self.parse_version(
                    self.get_file(release_data["assets"], "name", name_startwith)["name"]
                )
            case _:
                remote_version = self.parse_version("1.0")

        if compare_to == "commit":
            if local_commit == remote_commit:
                return False
        else:
            if local_version >= remote_version:
                return False

        # Retrieve file information based on name_startwith
        file = self.get_file(release_data["assets"], "name", name_startwith)
        if not file:
            return False

        # Extract download URL from file information
        url = file.get("browser_download_url")
        if not url:
            return False
        self.url = url

        # Check the file URL for any issues
        check_file = self.check_head(
            self.url, condition=lambda res: res.getheader("content-type", "").lower() == "application/octet-stream"
        )
        if not check_file:
            self.get_log().error(f"When checking update for {self.plugin_name} got url {self.url} but its not a file")
            return False

        self.commit = remote_commit
        # Update plugin version with the remote version
        if compare_to == "commit":
            self.plugin_version = None
        else:
            self.plugin_version = remote_version
        return True
