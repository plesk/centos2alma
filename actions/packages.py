from .action import ActivaAction

import subprocess
import os

import common


class RemovingPackages(ActivaAction):

    def __init__(self):
        self.name = "remove conflict packages"
        self.conflict_pkgs = [
            "openssl11-libs",
            "python36-PyYAML",
            "GeoIP",
            "psa-mod_proxy",
        ]

    def _filter_installed_packages(self, lookup_pkgs):
        pkgs = []
        process = subprocess.run(["rpm", "-q", "-a"], stdout=subprocess.PIPE, universal_newlines=True)
        for line in process.stdout.splitlines():
            end_of_name = 0
            while end_of_name != -1:
                end_of_name = line.find("-", end_of_name + 1)
                if line[end_of_name + 1].isnumeric():
                    break

            if end_of_name == -1:
                continue

            pkg_name = line[:end_of_name]
            if pkg_name in lookup_pkgs:
                pkgs.append(pkg_name)
        return pkgs

    def _prepare_action(self):
        for pkg in self._filter_installed_packages(self.conflict_pkgs):
            subprocess.check_call(["rpm", "-e", "--nodeps", pkg])

    def _post_action(self):
        pass


class ReinstallPleskComponents(ActivaAction):
    def __init__(self):
        self.name = "reintall components"

    def _prepare_action(self):
        components_pkgs = [
            "plesk-roundcube",
            "psa-phpmyadmin",
        ]

        for pkg in components_pkgs:
            find_pkg = subprocess.run(["rpm", "-q", "-a", pkg], stdout=subprocess.PIPE, universal_newlines=True)
            if len(find_pkg.stdout):
                subprocess.check_call(["rpm", "-e", "--nodeps", pkg])

    def _post_action(self):
        # We should reinstall psa-phpmyadmin over plesk installer to make sure every trigger
        # will be called. It's because triggers that creates phpmyadmin configuration files
        # expect plesk on board. Hence when we install the package in scoupe of temprorary OS
        # the file can't be created.
        common.log.info("Remove psa-phpmyadmin")
        subprocess.check_call(["rpm", "-e", "--nodeps", "psa-phpmyadmin"])
        common.log.info("do plesk installer update")
        subprocess.check_call(["plesk", "installer", "update"])
        common.log.info("installer update finished")

        components = [
            "roundcube"
        ]

        common.log.info("do plesk installer add roundcube")
        subprocess.check_call(["plesk", "installer", "add", "--components"] + components)
        common.log.info("plesk installer add roundcube finished")


class AdoptPleskRepositories(ActivaAction):
    def __init__(self):
        self.name = "adopt plesk repositories"

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
            common.replace_string(file.path, "rpm-CentOS-7", "rpm-RedHat-el8")

        subprocess.check_call(["dnf", "-y", "update"])
