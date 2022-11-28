from .action import Action

import subprocess
import os


class RemovingPackages(Action):

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


class FixMariadbDatabase(Action):
    def __init__(self):
        self.name = "fixing mysql databases"

    def _prepare_action(self):
        pass

    def _post_action(self):
        # We should be sure mariadb is started, otherwise restore woulden't work
        subprocess.check_call(["systemctl", "start", "mariadb"])

        with open('/etc/psa/.psa.shadow', 'r') as shadowfile:
            shadowdata = shadowfile.readline().rstrip()
            subprocess.check_call(["mysql_upgrade", "-uadmin", "-p" + shadowdata])
        # Also find a way to drop cookies, because it will ruin your day
        # Redelete it, because leapp going to install it in scoupe of convertation process, but it will no generate right configs


class ReinstallPleskComponents(Action):
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
        subprocess.check_call(["rpm", "-e", "--nodeps", "psa-phpmyadmin"])

        components = [
            "roundcube"
        ]
        subprocess.check_call(["plesk", "installer", "add", "--components"] + components)


class AdoptPleskRepositories(Action):
    def __init__(self):
        self.name = "adopt plesk repositories"

    def _prepare_action(self):
        pass

    def _post_action(self):
        for file in os.scandir("/etc/yum.repos.d"):
            if not file.name.startswith("plesk") or file.name[-5:] != ".repo":
                continue

            self._replace_string(file.path, "rpm-CentOS-7", "rpm-RedHat-el8")
            
        subprocess.check_call(["dnf", "update"])
