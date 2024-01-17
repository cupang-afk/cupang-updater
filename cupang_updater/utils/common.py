import re
import textwrap
from pathlib import Path
from typing import Any, Iterable

from packaging.version import InvalidVersion, Version


def list_get(iterable: Iterable, index: int, default: Any = None) -> Any:
    """
    Gets the element at the specified index in the iterable. Returns the default value if the index is out of range.

    Parameters:
    - iterable: The iterable to get the element from.
    - index: The index of the element to retrieve.
    - default: Default value to return if the index is out of range (default is None).

    Returns:
    - The element at the specified index, or the default value if the index is out of range.
    """
    # https://stackoverflow.com/a/28584046
    return (iterable[index:] + [default])[0]


def parse_version(version: str) -> Version:
    """
    Parses a version string.

    fallback to 1.0 if version string is invalid

    Parameters:
    - version: String representation of the version.

    Returns:
    - Parsed Version instance.
    """
    try:
        _version = Version(version).base_version
    except InvalidVersion:
        _match_version = re.search(r"([\d.]+)", version)
        if not _match_version:
            _version = "1.0"
        else:
            _version = "".join(_match_version.group(1))
    except Exception:
        _version = "1.0"
    return Version(_version)


def ensure_path(path: str | Path):
    """
    Ensures that the input is a Path object. If it's a string, converts it to a Path.

    Parameters:
    - path: Input path as a string or Path object.

    Returns:
    - Path object.
    """
    return path if isinstance(path, Path) else Path(path)


def reindent(text: str, size: int, ch: str = " "):
    """
    Removes existing indentation from the text and applies a new indentation.

    Parameters:
    - text: Input text with existing indentation.
    - size: Number of spaces for the new indentation.
    - ch: Character used for indentation (default is space).

    Returns:
    - Text with the new indentation applied.
    """
    if not getattr(reindent, "re_sub", None):
        reindent.re_sub: re.Pattern = re.compile(r"(?<=\S) +")

    # remove extra spaces
    text = reindent.re_sub.sub(" ", text)

    return textwrap.indent(textwrap.dedent(text), ch * size)
