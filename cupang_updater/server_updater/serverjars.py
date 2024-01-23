import json
from http import HTTPStatus
from http.client import HTTPResponse

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

        self.server_category: str = None
        self.server_name: str = None
        self.update_data: dict = None
        self.url: str = None

    def get_build_number(self) -> int | None:
        return None  # serverjars doesn't have build number

    def get_url(self) -> str:
        return self.url

    def get_update(self, version: str):
        if self.update_data is not None:
            return self.update_data

        def return_empty():
            # Return an empty dictionary if update data is not available
            self.update_data = {}
            return self.update_data

        # Perform a GET request to retrieve update data
        headers = {"Accept": "application/json"}
        res = self.make_requests(
            self.make_url(
                self.api_url,
                "fetchDetails",
                self.server_category,
                f"{self.server_name}{f'/{version}' if version else ''}",
            ),
            headers=headers,
        )

        # Check the response and handle errors
        res = self.check_response(res, headers)
        if res is None:
            return return_empty()

        update_data: dict = json.loads(res.read())
        update_data = update_data.get("response")
        if not update_data:
            return return_empty()

        self.update_data = update_data
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
        for k, v in self.server_categories.items():
            if self.server_name in v:
                self.server_category = k
        if self.server_category is None:
            return False

        update_data = self.get_update(server_version)
        local_md5 = server_hash.md5()
        remote_md5 = update_data["md5"]

        if local_md5 == remote_md5:
            return False

        url = self.make_url(
            self.api_url,
            "fetchJar",
            self.server_category,
            f"{self.server_name}{f'/{server_version}' if server_version else ''}",
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
