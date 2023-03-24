# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction

import os
import shutil

from common import rpm, util


class LeapInstallation(ActiveAction):

    def __init__(self):
        self.name = "installing leapp"
        self.pkgs_to_install = [
            "leapp",
            "python2-leapp",
            "leapp-upgrade",
            "leapp-data-almalinux",
        ]

    def _prepare_action(self):
        if not rpm.is_package_installed("elevate-release"):
            util.logged_check_call(["yum", "install", "-y", "http://repo.almalinux.org/elevate/elevate-release-latest-el7.noarch.rpm"])

        util.logged_check_call(["yum", "install", "-y"] + self.pkgs_to_install)

    def _post_action(self):
        rpm.remove_packages(rpm.filter_installed_packages(self.pkgs_to_install + ["elevate-release"]))

        leapp_related_files = [
            "/root/tmp_leapp_py3/leapp",
        ]
        for file in leapp_related_files:
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

    def _revert_action(self):
        pass

    def estimate_prepare_time(self):
        return 40
