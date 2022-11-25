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
        self.reinstall_pkgs = [
            "psa-phpmyadmin",
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
        for pkg in self._filter_installed_packages(self.conflict_pkgs + self.reinstall_pkgs):
            subprocess.check_call(["rpm", "-e", "--nodeps", pkg])

    def _post_action(self):
        # Conflict packages shouldn't be reinstalled after a convertation because new once from
        # Alma repositories will be installed instead of them. The exception of it is a psa-mod_proxy,
        # that not needed at all, because the httpd package in new distros brings appropriate apache modules by itself.
        # Packages from the reinstall list will be installed by leapp.
        pass


class FixupWebmail(Action):
    def __init__(self):
        self.name = "fixing webmail"
        self.webmail = "roundcube"

    def _prepare_action(self):
        find_pkg = subprocess.run(["rpm", "-q", "-a", "plesk-" + self.webmail], stdout=subprocess.PIPE, universal_newlines=True)
        if len(find_pkg.stdout):
            subprocess.check_call(["rpm", "-e", "--nodeps", "plesk-" + self.webmail])

    def _post_action(self):
        # We have to install roundcuve by plesk installer to make sure the panel will recognize roundcube is installed
        subprocess.check_call(["plesk", "installer", "add", "--components", "roundcube"])



class FixupPhpMyAdmin
    def __init__(self):
        self.name = "fixing phpmyadmin"

    def _prepare_action(self):
        find_pkg = subprocess.run(["rpm", "-q", "-a", "psa-phpmyadmin"], stdout=subprocess.PIPE, universal_newlines=True)
        if len(find_pkg.stdout):
            subprocess.check_call(["rpm", "-e", "--nodeps", "psa-phpmyadmin"])

    def _post_action(self):
        # Find the way to do it
        # mysql_upgrade -uadmin -p`< /etc/psa/.psa.shadow `
        # subprocess.check_call(["rpm", "-e", "--nodeps", "psa-phpmyadmin"])
        # Also find a way to drop cookies, because it will ruin your day
        # Redelete it, because leapp going to install it in scoupe of convertation process, but it will no generate right configs
        subprocess.check_call(["rpm", "-e", "--nodeps", "psa-phpmyadmin"])
        subprocess.check_call(["plesk", "installer", "update"])


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
