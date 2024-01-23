import json
from http import HTTPStatus
from http.client import HTTPResponse
from typing import Any

import strictyaml as sy

from ..utils import FileHash
from .base.plugin_updater_base import PluginUpdaterBase


class JenkinsUpdater(PluginUpdaterBase):
    # Updater information
    name = "Jenkins"
    config_path = "jenkins"
    plugin_config_schema = sy.Map(
        {
            "url": sy.EmptyNone() | sy.Url(),
            "name_startwith": sy.EmptyNone() | sy.Str(),
            "build_number": sy.EmptyNone() | sy.Int(),
        }
    )
    plugin_config_default = """
        # url: jenkins url
        # name_startwith: file name start with this value, example "Geyser-Spigot"
        url:
        name_startwith:
        build_number:
    """
    api_path = "/api/json"
    last_successful_build_param = {"tree": "lastSuccessfulBuild[url]"}
    artifacts_param = {"tree": "artifacts[*]"}

    def __init__(self) -> None:
        super().__init__()
        self.plugin_name = None
        self.plugin_version = None

        self.jenkins_url: str = None
        self.jenkins_build_number: int = None
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
        updates = [("build_number", self.jenkins_build_number)]
        return updates

    def get_update_data(self, jenkins_url) -> dict:
        # Perform GET request for the latest successful build
        headers = {"Accept": "application/json"}
        res_latest_build = self.make_requests(
            self.make_url(jenkins_url, self.api_path, **self.last_successful_build_param),
            headers=headers,
        )

        # Check the response and handle errors
        res_latest_build = self.check_response(res_latest_build, headers)
        if res_latest_build is None:
            return None
        latest_build_data = json.loads(res_latest_build.read())

        # Perform GET request for artifact information
        res_artifact = self.make_requests(
            self.make_url(latest_build_data["lastSuccessfulBuild"]["url"], self.api_path),
            headers=headers,
        )
        res_artifact = self.check_response(res_artifact, headers)
        if res_artifact is None:
            return None

        # Set update_data to the artifact information
        return json.loads(res_artifact.read())

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
        self.plugin_name = plugin_name
        self.plugin_version = plugin_version
        plugin_config

        # Extract Jenkins URL from plugin configuration
        jenkins_url = plugin_config.get("url")
        if jenkins_url is None:
            return False

        # Extract name_startwith from plugin configuration
        name_startwith = plugin_config.get("name_startwith")
        if name_startwith is None:
            self.get_log().error(f"name_starwith {name_startwith}")
            return False

        # Retrieve update data from Jenkins
        update_data = self.get_update_data(jenkins_url)
        if not update_data:
            self.get_log().error(f"update_data {update_data}")
            return False

        # Extract local and remote build numbers
        local_build_number = plugin_config.get("build_number", 0)
        remote_build_number = int(update_data["number"])
        if local_build_number >= remote_build_number:
            self.get_log().error("a")
            return False

        # Retrieve file information based on name_startwith
        file = self.get_file(update_data["artifacts"], "fileName", name_startwith)
        if not file:
            self.get_log().error("no")
            return False

        # Construct the download URL
        url = self.make_url(jenkins_url, remote_build_number, "artifact", file["relativePath"])
        if not url:
            return False
        self.url = url

        # Check the file URL for any issues
        check_file = self.check_head(
            self.url,
            condition=lambda res: res.getheader("content-type", "").lower()
        )
        if not check_file:
            self.get_log().error(f"When checking update for {self.plugin_name} got url {self.url} but its not a file")
            return False

        # Reset plugin version to None as it may not be applicable for Jenkins updates
        self.plugin_version = None
        self.jenkins_build_number = remote_build_number
        return True
