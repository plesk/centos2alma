from .action import ActiveAction

import subprocess
import os

import common


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
        for pkg in common.filter_installed_packages(self.conflict_pkgs):
            common.remove_packages(pkg)

    def _post_action(self):
        pass


class ReinstallPleskComponents(ActiveAction):
    def __init__(self):
        self.name = "re-installing plesk components"

    def _prepare_action(self):
        components_pkgs = [
            "plesk-roundcube",
            "psa-phpmyadmin",
        ]

        for pkg in components_pkgs:
            if common.is_package_installed(pkg):
                common.remove_packages(pkg)

    def _post_action(self):
        # We should reinstall psa-phpmyadmin over plesk installer to make sure every trigger
        # will be called. It's because triggers that creates phpmyadmin configuration files
        # expect plesk on board. Hence when we install the package in scope of temporary OS
        # the file can't be created.
        common.remove_packages("psa-phpmyadmin")
        subprocess.check_call(["plesk", "installer", "update"])

        components = [
            "roundcube"
        ]

        subprocess.check_call(["plesk", "installer", "add", "--components"] + components)


class UpdatePlesk(ActiveAction):
    def __init__(self):
        self.name = "updating plesk"

    def _prepare_action(self):
        subprocess.check_call(["plesk", "installer", "update"])

    def _post_action(self):
        pass


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
            common.replace_string(file.path, "rpm-CentOS-7", "rpm-CentOS-8",
                                  lambda line: "PHP_7.1" in line or "PHP_7.2" in line or "PHP_7.3" in line)
            common.replace_string(file.path, "rpm-CentOS-7", "rpm-RedHat-el8")

        subprocess.check_call(["dnf", "-y", "update"])
