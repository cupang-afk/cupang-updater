from abc import abstractmethod

from ...base_class import UpdaterBase
from ...utils.hash import FileHash


class ServerUpdaterBase(UpdaterBase):
    """Abstract base class for updater server.

    Important: Set these class variables when creating a class

    ```python
    # Example CustomUpdater


    class CustomUpdater(ServerUpdater):
        name = "Custom Url Updater"
        server_type_list = ["custom_server"]
    ```

    Class variables that need to be set:

    - `name`: The updater name (set when creating the class).
    - `server_type_list`: The list of server types that the updater supports (set when creating the class).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The updater name.
        """
        ...

    @property
    @abstractmethod
    def server_type_list(self) -> list[str]:
        """
        List of server types supported by the updater.

        example: ["paper"]
        """
        ...

    @abstractmethod
    def check_update(
        self,
        server_type: str,
        server_version: str,
        server_hash: FileHash,
        build_number: int,
    ) -> bool:
        """Main function for checking updates.

        Determines whether an update is available.

        Return True if an update is available, otherwise False.

        Should never raise any exception
        """
        ...

    @abstractmethod
    def get_build_number(self) -> int | None:
        """
        Returns the build number.

        If an update is available, return the updated build number.
        For example, if the current build number is 100 and a new version is detected,
        return the new build number, i.e., 200.

        If the build number cannot be obtained from the update site,
        return None. In such cases, consider using another parameter, such as file hash, for comparison.
        """
        ...
