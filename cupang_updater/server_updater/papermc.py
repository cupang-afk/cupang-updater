import json
from http import HTTPStatus

from cupang_updater.utils.hash import FileHash

from .base.server_updater_base import ServerUpdaterBase


class PaperUpdater(ServerUpdaterBase):
    name = "PaperMC"
    server_type_list = ["paper", "waterfall"]
    api_url = "https://api.papermc.io/v2/projects"

    def __init__(self) -> None:
        super().__init__()

        self.url: str = None
        self.build_number: int = None

    def get_build_number(self) -> int | None:
        return self.build_number

    def get_url(self) -> str:
        return self.url

    def get_update(self, server_type: str, version: str):
        # Perform a GET request to retrieve builds data
        headers = {"Accept": "application/json"}
        res = self.make_requests(
            self.make_url(self.api_url, server_type, "versions", version, "builds"),
            headers=headers,
            condition=lambda res: HTTPStatus(res.getcode()) == HTTPStatus.OK
            and res.getheader("content-type", "").lower() == headers["Accept"].lower(),
        )
        if res is None:
            return None

        builds_data: dict = json.loads(res.read())
        sorted_build_data = {k["build"]: k for k in builds_data["builds"]}
        latest_build_data = sorted_build_data[max(sorted_build_data.keys())]
        return latest_build_data

    def check_update(self, server_type: str, server_version: str, server_hash: FileHash, build_number: int) -> bool:
        update_data = self.get_update(server_type, server_version)
        if not update_data:
            return False

        local_sha256 = server_hash.sha256()
        remote_sha256 = update_data["downloads"]["application"]["sha256"]

        if local_sha256 == remote_sha256:
            return False

        remote_build_number = update_data["build"]

        url = self.make_url(
            self.api_url,
            server_type,
            "versions",
            server_version,
            "builds",
            remote_build_number,
            "downloads",
            f"{server_type}-{server_version}-{remote_build_number}.jar",
        )
        self.url = url

        # Check the file URL for any issues
        check_file = self.check_head(
            self.url,
            condition=lambda res: res.getheader("content-type", "").lower()
            in ["application/java-archive", "application/zip"],
        )
        if not check_file:
            self.get_log().error(
                f"When checking update for {server_type} using {self.name} got url {self.url} but its not a file"
            )
            return False

        self.build_number = remote_build_number
        return True
