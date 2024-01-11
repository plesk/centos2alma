# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import os
import shutil

from common import action, rpm, util


class LeapInstallation(action.ActiveAction):

    def __init__(self):
        self.name = "installing leapp"
        self.pkgs_to_install = [
            "leapp-0.14.0-1.el7",
            "python2-leapp-0.14.0-1.el7",
            "leapp-data-almalinux-0.1-6.el7",
        ]

    def _prepare_action(self) -> None:
        if not rpm.is_package_installed("elevate-release"):
            util.logged_check_call(["/usr/bin/yum", "install", "-y", "https://repo.almalinux.org/elevate/elevate-release-latest-el7.noarch.rpm"])

        util.logged_check_call(["/usr/bin/yum", "install", "-y"] + self.pkgs_to_install)

    def _post_action(self) -> None:
        rpm.remove_packages(rpm.filter_installed_packages(self.pkgs_to_install + ["elevate-release"]))

        leapp_related_files = [
            "/root/tmp_leapp_py3/leapp",
        ]
        for file in leapp_related_files:
            if os.path.exists(file):
                os.unlink(file)

        leapp_related_directories = [
            "/etc/leapp",
            "/var/lib/leapp",
            "/var/log/leapp",
            "/usr/lib/python2.7/site-packages/leapp",
        ]
        for directory in leapp_related_directories:
            if os.path.exists(directory):
                shutil.rmtree(directory)

    def _revert_action(self) -> None:
        pass

    def estimate_prepare_time(self) -> int:
        return 40
