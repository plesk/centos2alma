from .action import ActiveAction

import subprocess
import common


class LeapInstallation(ActiveAction):

    def __init__(self):
        self.name = "installing leapp"

    def _prepare_action(self):
        if not common.is_package_installed("elevate-release"):
            subprocess.check_call(["yum", "install", "-y", "http://repo.almalinux.org/elevate/elevate-release-latest-el7.noarch.rpm"])

        pkgs_to_install = [
            "leapp-upgrade",
            "leapp-data-almalinux",
        ]

        subprocess.check_call(["yum", "install", "-y"] + pkgs_to_install)

    def _post_action(self):
        # Todo. We could actually remove installed leap packages at the end
        pass

    def _revert_action(self):
        pass
