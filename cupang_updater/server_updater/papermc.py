import json
from http import HTTPStatus
from http.client import HTTPResponse

from cupang_updater.utils.hash import FileHash

from .base.server_updater_base import ServerUpdaterBase


class PaperUpdater(ServerUpdaterBase):
    name = "PaperMC"
    server_type_list = ["paper", "waterfall"]
    api_url = "https://api.papermc.io/v2/projects"

    def __init__(self) -> None:
        super().__init__()

        self.server_name: str = None
        self.update_data: dict = None
        self.url: str = None
        self.build_number: int = None

    def get_build_number(self) -> int | None:
        return self.build_number

    def get_url(self) -> str:
        return self.url

    def get_update(self, version: str):
        if self.update_data is not None:
            return self.update_data

        def return_empty():
            # Return an empty dictionary if update data is not available
            self.update_data = {}
            return self.update_data

        # Perform a GET request to retrieve builds data
        headers = {"Accept": "application/json"}
        res = self.make_requests(
            self.make_url(self.api_url, self.server_name, "versions", version, "builds"),
            headers=headers,
        )

        # Check the response and handle errors
        res = self.check_response(res, headers)
        if res is None:
            return return_empty()

        builds_data: dict = json.loads(res.read())
        sorted_build_data = {k["build"]: k for k in builds_data["builds"]}
        latest_build_data = sorted_build_data[max(sorted_build_data.keys())]
        self.update_data = latest_build_data
        return self.update_data

    def check_response(self, res: HTTPResponse | None, headers: dict) -> HTTPResponse | None:
        # Check the HTTP response for errors and return the response or None
        if res is None:
            self.get_log().error(f"Failed to fetch data for {self.server_name} because response is empty")
            return

        res_code = HTTPStatus(res.getcode())
        if res_code != HTTPStatus.OK:
            self.get_log().error(
                f"Failed to fetch data for {self.server_name} " f"because {res_code.value} {res_code.phrase}"
            )
            return

        content_type = res.getheader("content-type")
        if content_type is None:
            self.get_log().error(f"Requesting {headers['Accept']} for {self.server_name} but got None")
            return

        # Check if the content type matches the expected value
        if headers["Accept"] not in content_type.split(";"):
            self.get_log().error(f"Requesting {headers['Accept']} for {self.server_name} " f"but got {content_type}")
            return
        return res

    def check_update(self, server_type: str, server_version: str, server_hash: FileHash, build_number: int) -> bool:
        self.server_name = server_type

        update_data = self.get_update(server_version)

        local_sha256 = server_hash.sha256()
        remote_sha256 = update_data["downloads"]["application"]["sha256"]

        if local_sha256 == remote_sha256:
            return False

        remote_build_number = update_data["build"]

        url = self.make_url(
            self.api_url,
            self.server_name,
            "versions",
            server_version,
            "builds",
            remote_build_number,
            "downloads",
            f"{self.server_name}-{server_version}-{remote_build_number}.jar",
        )
        self.url = url

        # Check the file URL for any issues
        check_file = self.check_head(
            self.url,
            condition=lambda res: res.getheader("content-type", "").lower()
        )
        if not check_file:
            self.get_log().error(
                f"When checking update for {server_type} using {self.name} got url {self.url} but its not a file"
            )
            return False

        self.build_number = remote_build_number
        return True
