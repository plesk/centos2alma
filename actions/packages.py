from .action import Action

import subprocess
import os


class RemovingPackages(Action):

    def __init__(self):
        self.name = "remove conflict packages"

    def _get_installed_packages(self, lookup_pkgs):
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
        conflict_pkgs = [
            "openssl11-libs",
            "python36-PyYAML",
            "GeoIP",
            "psa-mod_proxy",
        ]
        reinstall_pkgs = [
            "plesk-roundcube",
            "psa-phpmyadmin",
        ]

        for pkg in self._get_installed_packages(conflict_pkgs + reinstall_pkgs):
            subprocess.check_call(["rpm", "-e", "--nodeps", pkg])

        with open("/etc/leapp/transaction/to_install", "a") as leapp_installation_list:
            for pkg in reinstall_pkgs:
                leapp_installation_list.write("{}\n".format(pkg))

    def _post_action(self):
        # Conflict packages shouldn't be reinstalled after a convertation because new once from
        # Alma repositories will be installed instead of them. The exception of it is a psa-mod_proxy,
        # that not needed at all, because the httpd package in new distros brings appropriate apache modules by itself.
        # Packages from the reinstall list will be installed by leapp.
        pass


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
