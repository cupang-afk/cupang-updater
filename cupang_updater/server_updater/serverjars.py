import json
from http import HTTPStatus

from cupang_updater.utils.hash import FileHash

from .base.server_updater_base import ServerUpdaterBase


class ServerjarsUpdater(ServerUpdaterBase):
    name = "Serverjars"
    server_type_list = ["purpur", "bungeecord", "velocity"]
    api_url = "https://serverjars.com/api"
    server_categories = {
        "proxies": [
            "waterfall",
            "bungeecord",
            "velocity",
        ],
        "servers": [
            "purpur",
        ],
    }

    def __init__(self) -> None:
        super().__init__()

        self.update_data: dict = None
        self.url: str = None

    def get_build_number(self) -> int | None:
        return None  # serverjars doesn't have build number

    def get_url(self) -> str:
        return self.url

    def get_update(self, server_type: str, server_category: str, version: str) -> dict | None:
        # Perform a GET request to retrieve update data
        headers = {"Accept": "application/json"}
        res = self.make_requests(
            self.make_url(
                self.api_url,
                "fetchDetails",
                server_category,
                f"{server_type}{f'/{version}' if version else ''}",
            ),
            headers=headers,
            condition=lambda res: HTTPStatus(res.getcode()) == HTTPStatus.OK
            and res.getheader("content-type", "").lower() == headers["Accept"].lower(),
        )
        if res is None:
            return None

        update_data: dict = json.loads(res.read())
        if update_data["status"].lower() != "success":
            return None
        response_data = update_data["response"]
        return response_data

    def check_update(self, server_type: str, server_version: str, server_hash: FileHash, build_number: int) -> bool:
        server_category = None
        for k, v in self.server_categories.items():
            if server_type in v:
                server_category = k
        if server_category is None:
            return False

        update_data = self.get_update(server_type, server_category, server_version)
        local_md5 = server_hash.md5()
        remote_md5 = update_data["md5"]

        if local_md5 == remote_md5:
            return False

        url = self.make_url(
            self.api_url,
            "fetchJar",
            server_category,
            f"{server_type}{f'/{server_version}' if server_version else ''}",
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
                f"When checking update for server using {self.name} got url {self.url} but its not a file"
            )
            return False

        return True
