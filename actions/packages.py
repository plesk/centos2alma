# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction

import subprocess
import os

import common
from common import leapp_configs, util


class RemovingPackages(ActiveAction):

    def __init__(self):
        self.name = "remove conflict packages"
        self.conflict_pkgs = [
            "openssl11-libs",
            "python36-PyYAML",
            "GeoIP",
            "psa-mod_proxy",
        ]

    def _prepare_action(self):
        common.remove_packages(common.filter_installed_packages(self.conflict_pkgs))

    def _post_action(self):
        pass

    def _revert_action(self):
        common.install_packages(self.conflict_pkgs)

    def estimate_prepare_time(self):
        return 2

    def estimate_revert_time(self):
        return 10


class ReinstallPleskComponents(ActiveAction):
    def __init__(self):
        self.name = "re-installing plesk components"

    def _prepare_action(self):
        components_pkgs = [
            "plesk-roundcube",
            "psa-phpmyadmin",
        ]

        common.remove_packages(common.filter_installed_packages(components_pkgs))

    def _post_action(self):
        # We should reinstall psa-phpmyadmin over plesk installer to make sure every trigger
        # will be called. It's because triggers that creates phpmyadmin configuration files
        # expect plesk on board. Hence when we install the package in scope of temporary OS
        # the file can't be created.
        common.remove_packages(["psa-phpmyadmin"])
        util.logged_check_call(["plesk", "installer", "update"])

        util.logged_check_call(["plesk", "installer", "add", "--components", "roundcube"])

    def _revert_action(self):
        util.logged_check_call(["plesk", "installer", "update"])
        util.logged_check_call(["plesk", "installer", "add", "--components", "roundcube"])

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        return 2 * 60

    def estimate_revert_time(self):
        return 2 * 60


class UpdatePlesk(ActiveAction):
    def __init__(self):
        self.name = "updating plesk"

    def _prepare_action(self):
        util.logged_check_call(["plesk", "installer", "update"])

    def _post_action(self):
        pass

    def _revert_action(self):
        pass

    def estimate_prepare_time(self):
        return 3 * 60


class AdoptPleskRepositories(ActiveAction):
    def __init__(self):
        self.name = "adopting plesk repositories"

    def _prepare_action(self):
        pass

    def _post_action(self):
        for file in os.scandir("/etc/yum.repos.d"):
            if not file.name.startswith("plesk") or file.name[-5:] != ".repo":
                continue

            common.remove_repositories(file.path, [
                "PLESK_17_PHP52", "PLESK_17_PHP53", "PLESK_17_PHP54",
                "PLESK_17_PHP55", "PLESK_17_PHP56", "PLESK_17_PHP70",
            ])
            common.adopt_repositories(file.path)

        util.logged_check_call(["dnf", "-y", "update"])

    def _revert_action(self):
        pass

    def estimate_post_time(self):
        return 2 * 60


class AdoptKolabRepositories(ActiveAction):
    def __init__(self):
        self.name = "adopting kolab repositories"

    def _is_required(self):
        for file in os.scandir("/etc/yum.repos.d"):
            if file.name.startswith("kolab") and file.name[-5:] == ".repo":
                return True

        return False

    def _prepare_action(self):
        repofiles = []

        for file in os.scandir("/etc/yum.repos.d"):
            if file.name.startswith("kolab") and file.name[-5:] == ".repo":
                repofiles.append(file.path)

        leapp_configs.add_repositories_mapping(repofiles, ignore=["kolab-16-source",
                                                                  "kolab-16-testing-source",
                                                                  "kolab-16-testing-candidate-source"])

    def _post_action(self):
        for file in os.scandir("/etc/yum.repos.d"):
            if not file.name.startswith("kolab") or file.name[-5:] != ".repo":
                continue

            common.adopt_repositories(file.path)

        util.logged_check_call(["dnf", "-y", "update"])

    def _revert_action(self):
        pass

    def estimate_prepare_time(self):
        return 30

    def estimate_post_time(self):
        return 2 * 60
