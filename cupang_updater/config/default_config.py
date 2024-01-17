# flake8: noqa
from textwrap import dedent

default_config = dedent(
    """
    #
    # *  ██████╗██╗   ██╗██████╗  █████╗ ███╗   ██╗ ██████╗
    # * ██╔════╝██║   ██║██╔══██╗██╔══██╗████╗  ██║██╔════╝
    # * ██║     ██║   ██║██████╔╝███████║██╔██╗ ██║██║  ███╗
    # * ██║     ██║   ██║██╔═══╝ ██╔══██║██║╚██╗██║██║   ██║
    # * ╚██████╗╚██████╔╝██║     ██║  ██║██║ ╚████║╚██████╔╝
    # *  ╚═════╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝
    # *
    # * ██╗   ██╗██████╗ ██████╗  █████╗ ████████╗███████╗██████╗
    # * ██║   ██║██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝██╔══██╗
    # * ██║   ██║██████╔╝██║  ██║███████║   ██║   █████╗  ██████╔╝
    # * ██║   ██║██╔═══╝ ██║  ██║██╔══██║   ██║   ██╔══╝  ██╔══██╗
    # * ╚██████╔╝██║     ██████╔╝██║  ██║   ██║   ███████╗██║  ██║
    # *  ╚═════╝ ╚═╝     ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
    #
    #

    settings:
      last_update:
      server_folder:
      update_cooldown: 12 # in hour
      keep_removed_plugins: true # false if you want to remove "removed" plugins in config
      update_order: # top to bottom
    server:
      enable: false # true if you want to auto update the server
      file: server.jar
      type: purpur
      version: 1.19.4 # a version number like 1.20.4
      build_number: # if you change server.version, empty this
      custom_download_url:
      hashes:
        md5:
        sha1:
        sha256:
        sha512:
    updater_settings:
    plugins:
    """
)
