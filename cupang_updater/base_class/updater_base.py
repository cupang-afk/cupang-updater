import http.client
import urllib.error
from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Callable, final

from packaging.version import Version

from ..logger import LoggerManager
from ..utils import make_requests, make_url, parse_version


class UpdaterBase(ABC):
    """
    Abstract base class for updater.

    Warning:
        Shouldn't use this outside of internal usage as this don't serve any purpose.
        Use `cupang_updater.updater.PluginManagerBase` instead.

    Note:
        Provides a framework for creating updaters with required functions
        and attributes for checking and applying updates.

    Tip:
        Subclasses should implement the abstract methods to create a specific updater.


    Class variables that need to be set:

    - `name`: The updater name (set when creating the class).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The updater name.
        """
        ...

    @abstractmethod
    def check_update(
        self,
        *args,
        **kwargs,
    ) -> bool:
        """Main function for checking updates.

        Determines whether an update is available.

        It's recommended to check `plugin_config` before proceeding further.

        Return True if an update is available, otherwise False.

        Should never raise any exception
        """
        ...

    @abstractmethod
    def get_url(self) -> str:
        """
        Return download url
        """
        ...

    def get_headers(self) -> dict[str, Any]:
        """
        Return headers to be use when downloading file

        Optional
        """
        ...

    @final
    def get_log(self) -> Logger:
        """
        Get the logger for the updater.
        """
        return LoggerManager().get_log().getChild(self.name)

    @final
    @staticmethod
    def make_url(url: str, *url_paths, **url_params) -> str:
        """
        Construct a URL by combining the base URL, paths, and query parameters.

        Example Usage:

        ```python
            url = self.make_url("https://google.com", "search", q="vim")
            print(url)  # https://google.com/search?q=vim
        ```
        """
        return make_url(url, *url_paths, **url_params)

    @final
    def make_requests(
        self, url: str, method: str = "GET", headers: dict[str, str] = None
    ) -> http.client.HTTPResponse | None:
        """Safely create a request using urllib.request.

        Recommended to use this method instead of creating a new one.

        Return A HTTPResponse object if successful, otherwise None.
        """

        try:
            res = make_requests(url, method=method, headers=headers)
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            self.get_log().error(
                f"Error while requesting data from {url}\n    "
                f"{type(e).__qualname__}: {e}\n"
                f"Executed with arguments (url={url}, method={method}, headers={headers})"
            )
            return
        return res

    @final
    def check_head(
        self,
        url: str,
        *,
        headers: dict[str, str] = None,
        condition: Callable[[HTTPResponse], bool],
    ) -> bool:
        """Check the header of a URL, for example, to verify if it points to a file

        Args:
            url (str): The URL to check
            condition (Callable[[HTTPResponse], bool]): A callable that takes an HTTPResponse object and returns a boolean

        Returns:
            bool: True if the check passed, False otherwise.
        """

        res = self.make_requests(url, method="HEAD", headers=headers)
        if res is None:
            return False

        if not condition(res):
            return False

        return True

    @final
    @staticmethod
    def parse_version(version: str) -> Version:
        """Parse any kind of version string.

        Reverts to version 1.0 if the version string is not found.

        Return a Version object representing the parsed version.
        """
        return parse_version(version)
