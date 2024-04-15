import json
from http import HTTPStatus

from cupang_updater.utils.hash import FileHash

from .base.server_updater_base import ServerUpdaterBase


class PurpurUpdater(ServerUpdaterBase):
    name = "PurpurMC"
    server_type_list = ["purpur"]
    api_url = "https://api.purpurmc.org/v2/purpur/"

    def __init__(self) -> None:
        super().__init__()

        self.url: str = None
        self.build_number: int = None

    def get_build_number(self) -> int | None:
        return self.build_number

    def get_url(self) -> str:
        return self.url

    def get_update(self, version: str):
        # Perform a GET request to retrieve builds data
        headers = {"Accept": "application/json"}
        res = self.make_requests(
            self.make_url(self.api_url, version),
            headers=headers,
            condition=lambda res: HTTPStatus(res.getcode()) == HTTPStatus.OK
            and res.getheader("content-type", "").lower() == headers["Accept"].lower(),
        )
        if res is None:
            return None

        builds_data: dict = json.loads(res.read())
        return builds_data

    def check_update(
        self, server_type: str, server_version: str, server_hash: FileHash, build_number: int
    ) -> bool:
        update_data = self.get_update(server_version)
        if not update_data:
            return False

        remote_build_number: int = int(update_data["builds"]["latest"])

        if remote_build_number == build_number:
            return False

        url = self.make_url(self.api_url, server_version, remote_build_number, "download")
        self.url = url

        # Check the file URL for any issues
        check_file = self.check_head(
            self.url,
            condition=lambda res: res.getheader("content-type", "").lower()
            == "application/octet-stream",
        )
        if not check_file:
            self.get_log().error(
                f"When checking update for {server_type} using {self.name} got url {self.url} but its not a file"
            )
            return False

        self.build_number = remote_build_number
        return True
