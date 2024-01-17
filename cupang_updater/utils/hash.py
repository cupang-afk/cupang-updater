import hashlib
from pathlib import Path
from typing import BinaryIO

from .common import ensure_path


class FileHash:
    """Provides methods to compute hash values using MD5, SHA-1, SHA-256, and SHA-512 algorithms.

    ```python
    # Example Usage:
    file_hasher = FileHash("example.txt")
    md5_hash = file_hasher.md5()
    sha256_hash = file_hasher.sha256()
    ```

    """

    DEFAULT_CHUNK_SIZE = 64 * 2**10

    def __init__(self, file: Path | str):
        self.file = ensure_path(file)
        self.hashes: dict[str, str] = {}

    @classmethod
    def with_new_file(cls, file: Path | str):
        """
        Creates a new FileHash instance for the specified file.

        Useful if you have already initiated FileHash.

        Parameters:
        - file: Path to the file or a file-like object.
        """
        return cls(file)

    @classmethod
    def with_known_hashes(cls, file: Path | str, known_hashes: dict[str, str] = None):
        """
        Creates a FileHash instance for the specified file with pre-existing known hash values.

        Parameters:
        - file: Path to the file or a file-like object.
        - known_hashes: Dictionary of known hash values.
        """

        instance = cls(file)
        if known_hashes is not None:
            instance.hashes.update(known_hashes)
        return instance

    def __hash(self, stream: BinaryIO, hash_tool) -> str:
        while True:
            data = stream.read(self.DEFAULT_CHUNK_SIZE)
            if not data:
                break
            hash_tool.update(data)
        return hash_tool.hexdigest()

    def __get_hash(self, hash_name: str) -> str:
        hash = self.hashes.get(hash_name)
        if hash is not None:
            return hash

        hash_tool = hashlib.new(hash_name)
        hash = self.__hash(self.file.open("rb"), hash_tool)
        self.hashes[hash_tool] = hash
        return hash

    def md5(self) -> str:
        """
        Computes and returns the MD5 hash value of the file.
        """
        return self.__get_hash("md5")

    def sha1(self) -> str:
        """
        Computes and returns the SHA-1 hash value of the file.
        """
        return self.__get_hash("sha1")

    def sha256(self) -> str:
        """
        Computes and returns the SHA-256 hash value of the file.
        """
        return self.__get_hash("sha256")

    def sha512(self) -> str:
        """
        Computes and returns the SHA-512 hash value of the file.
        """
        return self.__get_hash("sha512")
