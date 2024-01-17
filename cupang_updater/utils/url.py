import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPResponse

from ..app.app_config import app_headers


# from https://stackoverflow.com/a/43934565
def make_url(base_url: str, *url_paths: str, **url_params: dict[str, str]):
    """
    Construct a URL by combining the base URL, paths, and query parameters.

    :param base_url: Base URL.
    :type base_url: str
    :param url_paths: Additional path components to append to the URL.
    :param url_params: Query parameters to include in the URL.
    :return: The constructed URL.
    :rtype: str

    Example Usage:

    .. code-block:: python

        url = make_url("https://google.com", "search", q="vim")
        print(url)  # https://google.com/search?q=vim
    """
    url = base_url.rstrip("/")
    for url_path in url_paths:
        _url_path = str(url_path).strip("/")
        url = "{}/{}".format(url, _url_path)
    if url_params:
        url = "{}?{}".format(url, urllib.parse.urlencode(url_params))
    return url


def make_requests(url: str, method: str = "GET", headers: dict[str, str] = None) -> HTTPResponse:
    """
    Safely create a request using urllib.request.

    Recommended to use this method instead of creating a new one.

    :param url: The URL for the request.
    :type url: str
    :param method: The HTTP method to use (default is "GET").
    :type method: str
    :param headers: Optional headers for the request.
    :type headers: dict[str, str] | None
    :return: A HTTPResponse object if successful, otherwise None.
    :rtype: HTTPResponse | None
    """
    if not headers:
        headers = {}
    headers = {**app_headers, **headers}
    res: HTTPResponse = urllib.request.urlopen(
        urllib.request.Request(
            url,
            method=method,
            headers=headers,
        )
    )
    return res
