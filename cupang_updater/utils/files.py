import shutil
import stat
from pathlib import Path


def file_rm_suffix(file: Path):
    """
    Removes the suffix from a given file Path and returns the modified Path.

    Parameters:
    - file: Path to the file.

    Returns:
    - Modified Path without the file suffix.
    """
    if file.suffix == "":
        return file
    return file_rm_suffix(file.with_name(file.stem))


def dir_rmdir(dir: Path):
    """
    Recursively removes the directory and its contents.

    Parameters:
    - dir: Path to the directory to be removed.
    """
    for _ in dir.rglob("*"):
        _.chmod(stat.S_IWRITE)
    shutil.rmtree(dir.absolute())
