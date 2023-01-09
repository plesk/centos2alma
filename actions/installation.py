from .action import ActiveAction

import subprocess


class LeapInstallation(ActiveAction):

    def __init__(self):
        self.name = "install leapp"

    def _is_pkg_installed(self, pkg_name):
        res = subprocess.run(["rpm", "--quiet", "--query", pkg_name])
        return res.returncode == 0

    def _prepare_action(self):
        if not self._is_pkg_installed("elevate-release"):
            subprocess.check_call(["yum", "install", "-y", "http://repo.almalinux.org/elevate/elevate-release-latest-el7.noarch.rpm"])

        pkgs_to_install = [
            "leapp-upgrade",
            "leapp-data-almalinux",
        ]

        subprocess.check_call(["yum", "install", "-y"] + pkgs_to_install)

    def _post_action(self):
        # Todo. We could actually remove installed leap packages at the end
        pass
