# Copyright 1999 - 2024. Plesk International GmbH. All rights reserved.
import os
import shutil

from pleskdistup.common import action, files, rpm, util


class LeapInstallation(action.ActiveAction):

    def __init__(self):
        self.name = "installing leapp"
        self.pkgs_to_install = [
            "leapp-0.18.0-1.el7",
            "python2-leapp-0.18.0-1.el7",
            "leapp-data-almalinux-0.4-5.el7.20240827",
            "leapp-deps-0.18.0-1.el7",
            "leapp-upgrade-el7toel8-0.21.0-2.el7",
            "leapp-upgrade-el7toel8-deps-0.21.0-2.el7",
        ]

    def _remove_previous_installation(self) -> None:
        # Remove previously installed leapp packages to make sure we will install the correct version
        pkgs_to_remove = rpm.filter_installed_packages([
            "leapp",
            "python2-leapp",
            "leapp-data-almalinux",
            "leapp-deps",
            "leapp-upgrade-el7toel8",
            "leapp-upgrade-el7toel8-deps",
        ])
        if pkgs_to_remove:
            util.logged_check_call(["/usr/bin/yum", "remove", "-y"] + pkgs_to_remove)

        # The directory contains leapp-data package configurations, which causes problems with
        # the package installation. So we have to remove it, to reinstall package from scratch.
        for system_upgrade_link in files.find_files_case_insensitive("/etc/leapp/repos.d", "system_upgrade*"):
            os.unlink(system_upgrade_link)

    def _prepare_action(self) -> action.ActionResult:
        if not rpm.is_package_installed("elevate-release"):
            util.logged_check_call(["/usr/bin/yum", "install", "-y", "https://repo.almalinux.org/elevate/elevate-release-latest-el7.noarch.rpm"])

        self._remove_previous_installation()

        util.logged_check_call(["/usr/bin/yum-config-manager", "--enable", "elevate"])

        util.logged_check_call(["/usr/bin/yum", "install", "-y"] + self.pkgs_to_install)
        # We want to prevent the leapp packages from being updated accidentally to
        # the latest version (for example by using 'yum update -y'). Therefore, we
        # should disable the 'elevate' repository. Additionally, this will prevent
        # the pre-checker from detecting leapp as outdated and prevent re-evaluation
        # on the next restart.
        util.logged_check_call(["/usr/bin/yum-config-manager", "--disable", "elevate"])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        rpm.remove_packages(
            rpm.filter_installed_packages(
                self.pkgs_to_install + ["elevate-release", "leapp-upgrade-el7toel8"]
            )
        )

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

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 40
