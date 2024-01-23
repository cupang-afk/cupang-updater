A Mincraft plugin downloader

This project are still undergoing the version will stay at 0.1.0 until i feel okay

### Install

```python
pip install git+https://github.com/cupang-afk/cupang-updater
```

### Usage

```shell
$ cupang-updater
```

running that will create `cupang-updater` folder in your working path,
inside you will have `config.yaml` that act as the configuration for each updater
this can be change using `--config PATH`

### Additional updater

by default this provide update check from bukkit, spigot, modrinth, github, jenkins, and also custom url

but you can extend that by adding your own updater script inside `cupang-updater/ext_updater`

this can be a `.py` file or a folder contain `main.py`

example `hangar.py`

```python
# PaperMC Hangar Updater

from http import HTTPStatus
from http.client import HTTPResponse
import json
from typing import Any
from cupang_updater.plugin_updater import PluginUpdaterBase
import strictyaml as sy

from cupang_updater.utils.hash import FileHash

# strictyaml scalar validator to check config platform value
class PlatformType(sy.Str):
    platform = ["paper", "waterfall", "velocity"]
    def validate_scalar(self, chunk):
        val: str = chunk.contents
        val = val.lower()
        if val not in self.platform:
            chunk.expecting_but_found(f"when expecting one of these: {self.platform}")
        return super().validate_scalar(chunk)

# strictyaml scalar validator to check if string is not empty
class NonEmptyStr(sy.Str):
    def validate_scalar(self, chunk):
        if chunk.contents == "":
            chunk.expecting_but_found("when expecting some string")
        return chunk.contents

# setup class
class HangarUpdater(PluginUpdaterBase):
    name = "Hangar"
    config_path = "hangar"
    plugin_config_schema = sy.Map(
        {"id": sy.EmptyNone() | sy.Str(), "platform": sy.EmptyNone() | PlatformType(), "channel": NonEmptyStr()}
    )
    plugin_config_default = """
        # id: https://hangar.papermc.io/[author]/[your project id here]
        # platform: one of these, paper, waterfall, velocity
        # channel: update channel # Release, Snapshot, Alpha
        id:
        platform:
        channel: Release
    """
    api_url = "https://hangar.papermc.io/api/v1/projects"

    def __init__(self) -> None:
        super().__init__()
        self.plugin_name = None
        self.plugin_version = None
        self.plugin_hash = None

        self.url: str = None

    def get_plugin_name(self) -> str:
        # Return the plugin name
        return self.plugin_name

    def get_url(self) -> str:
        # Return the download URL
        return self.url

    def get_plugin_version(self) -> str | None:
        # Return the plugin version or None if not available
        return self.plugin_version

    def get_update_data(self, project_id: str, channel: str):
        # Perform a GET request to retrieve latest release version
        headers = {"Accept": "text/plain"}
        res_release = self.make_requests(
            self.make_url(self.api_url, project_id, "latest", channel=channel),
            headers=headers,
            condition=lambda res: HTTPStatus(res.getcode()) == HTTPStatus.OK
            and res.getheader("content-type", "").split(";", 1)[0].lower() == headers["Accept"].lower(),
        )
        if res_release is None:
            return None

        latest_version = res_release.read().decode()

        # Perform a GET request to retrieve update data
        headers = {"Accept": "application/json"}
        res_latest = self.make_requests(
            self.make_url(self.api_url, project_id, "versions", latest_version),
            headers=headers,
            condition=lambda res: HTTPStatus(res.getcode()) == HTTPStatus.OK
            and res.getheader("content-type", "").split(";", 1)[0].lower() == headers["Accept"].lower(),
        )
        if res_latest is None:
            return None

        res_latest = json.loads(res_latest.read())
        return res_latest

    def check_update(
        self,
        plugin_name: str,
        plugin_version: str,
        plugin_hash: FileHash,
        plugin_config: dict[str, str] | Any,
        updater_config: dict[str, str] | Any | None = None,
    ) -> bool:
        self.plugin_name = plugin_name
        self.plugin_version = plugin_version
        self.plugin_hash = plugin_hash
        project_id = plugin_config.get("id")
        project_platform = plugin_config.get("platform")
        project_channel = plugin_config.get("channel")

        if project_id is None:
            return False
        if project_platform is None:
            return False
        project_data = self.get_update_data(project_id, project_channel)
        if project_data is None:
            return False

        local_version = self.parse_version(plugin_version)
        remote_version = self.parse_version(project_data["name"])
        if local_version >= remote_version:
            return False

        self.url = self.make_url(
            self.api_url, project_id, "versions", project_data["name"], project_platform.upper(), "download"
        )

        # Check the file URL for any issues
        check_file = self.check_head(
            self.url,
            condition=lambda res: res.getheader("content-type", "").lower()
            in ["application/java-archive", "application/zip"],
        )
        if not check_file:
            self.get_log().error(f"When checking update for {self.plugin_name} got url {self.url} but its not a file")
            return False

        self.plugin_version = str(project_data["name"])
        return True


# Register the updater
HangarUpdater().register()
```

above is an example for [Hangar by PaperMC](https://hangar.papermc.io/) plugins website

you can check [PluginUpdaterBase](cupang_updater/plugin_updater/base/plugin_updater_base.py) if you wish to build your own

additionally, for server updater [ServerUpdaterBase](cupang_updater/server_updater/base/server_updater_base.py) example: [PaperMC Updater](cupang_updater/server_updater/papermc.py)

> [!WARNING]
> looking at how this implemented in [ExtManager](cupang_updater/manager/ext_manager.py)
>
> this is powerfull as using `exec()` so, use on your own risk
>
> PR are welcome to reduce this risk

### Compiling into binary executable

use [pyinstaller](https://www.pyinstaller.org/)

```bash
$ pyinstaller cupang-updater.spec
```

this will create `dist/cupang-updater-bin`

doing this enable you to use the updater to the remote server that can execute a binary program

if not then you need to wrap the `cupang-updater-bin` to a `.jar` file

example flow

```
.jar executed by java -jar > extract cupang-updater-bin > execute extracted cupang-updater-bin from the .jar
```

> [!NOTE]
> your ext_updater cannot use 3rd party modules because the binary cannot import 3rd party modules from your python site-packages, unless you add it using --hidden-import
>
> by using cupang-updater.spec file you can add it by adding argument
>
> ```bash
> $ pyinstaller cupang-updater.spec -- --extra-hidden-import modules
> ```

### TODO

- [ ] create error class as i usually use Exception all over the place which is bad idea
- [ ] make `--config-dir` work again because of [fb7bae7](https://github.com/cupang-afk/cupang-updater/commit/fb7bae71eaa750edabef9213f7798cb4a1ac9a37)
- [ ] make [ExtManager.register](cupang_updater/manager/ext_manager.py) more secure
- [ ] make use [PEP 621](https://peps.python.org/pep-0621/)
