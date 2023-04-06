# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction

from common import files, leapp_configs, log, rpm, util

import os


class RemovingPleskConflictPackages(ActiveAction):

    def __init__(self):
        self.name = "remove conflict packages"
        self.conflict_pkgs = [
            "openssl11-libs",
            "python36-PyYAML",
            "GeoIP",
            "psa-mod_proxy",
        ]

    def _prepare_action(self):
        rpm.remove_packages(rpm.filter_installed_packages(self.conflict_pkgs))

    def _post_action(self):
        pass

    def _revert_action(self):
        rpm.install_packages(self.conflict_pkgs)

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

        rpm.remove_packages(rpm.filter_installed_packages(components_pkgs))

    def _post_action(self):
        # We should reinstall psa-phpmyadmin over plesk installer to make sure every trigger
        # will be called. It's because triggers that creates phpmyadmin configuration files
        # expect plesk on board. Hence when we install the package in scope of temporary OS
        # the file can't be created.
        rpm.remove_packages(["psa-phpmyadmin"])
        util.logged_check_call(["/usr/sbin/plesk", "installer", "update"])

        util.logged_check_call(["/usr/sbin/plesk", "installer", "add", "--components", "roundcube"])

    def _revert_action(self):
        util.logged_check_call(["/usr/sbin/plesk", "installer", "update"])
        util.logged_check_call(["/usr/sbin/plesk", "installer", "add", "--components", "roundcube"])

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        return 2 * 60

    def estimate_revert_time(self):
        return 2 * 60


class ReinstallConflictPackages(ActiveAction):
    def __init__(self):
        self.name = "re-installing conflict packages"
        self.removed_packages_file = "/usr/local/psa/tmp/removed_packages.txt"
        self.conflict_pkgs_map = {
            "python36-six": "python3-six",
            "python36-urllib3": "python3-urllib3",
            "python36-requests": "python3-requests",
            "python36-idna": "python3-idna",
            "python36-chardet": "python3-chardet",
            "libpcap": "libpcap",
        }

    def _is_required(self):
        return len(rpm.filter_installed_packages(self.conflict_pkgs_map.keys())) > 0

    def _prepare_action(self):
        packages_to_remove = rpm.filter_installed_packages(self.conflict_pkgs_map.keys())

        rpm.remove_packages(packages_to_remove)

        with open(self.removed_packages_file, "w") as f:
            f.write("\n".join(packages_to_remove))

    def _post_action(self):
        if not os.path.exists(self.removed_packages_file):
            log.warn("File with removed packages list is not exists. While the action itself was not skipped. Skip reinstalling packages.")
            return

        with open(self.removed_packages_file, "r") as f:
            packages_to_install = [self.conflict_pkgs_map[pkg] for pkg in f.read().splitlines()]
            rpm.install_packages(packages_to_install)

        os.unlink(self.removed_packages_file)

    def _revert_action(self):
        if not os.path.exists(self.removed_packages_file):
            log.warn("File with removed packages list is not exists. While the action itself was not skipped. Skip reinstalling packages.")
            return

        with open(self.removed_packages_file, "r") as f:
            packages_to_install = f.read().splitlines()
            rpm.install_packages(packages_to_install)

        os.unlink(self.removed_packages_file)

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        return 60

    def estimate_revert_time(self):
        return 60


class UpdatePlesk(ActiveAction):
    def __init__(self):
        self.name = "updating plesk"

    def _prepare_action(self):
        util.logged_check_call(["/usr/sbin/plesk", "installer", "update"])

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
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*.repo"]):
            files.remove_repositories(file, [
                "PLESK_17_PHP52", "PLESK_17_PHP53", "PLESK_17_PHP54",
                "PLESK_17_PHP55", "PLESK_17_PHP56", "PLESK_17_PHP70",
            ])
            leapp_configs.adopt_repositories(file)

        util.logged_check_call(["/usr/bin/dnf", "-y", "update"])

    def _revert_action(self):
        pass

    def estimate_post_time(self):
        return 2 * 60
