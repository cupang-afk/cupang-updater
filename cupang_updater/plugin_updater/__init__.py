# base class
from .base.plugin_updater_base import PluginUpdaterBase

# default updater
from .bukkit import BukkitUpdater
from .custom import CustomUpdater
from .github import GithubUpdater
from .jenkins import JenkinsUpdater
from .modrinth import ModrinthUpdater
from .spigot import SpigotUpdater
