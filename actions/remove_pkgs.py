from .action import Action

import subprocess


class RemovingPackages(Action):

    def __init__(self):
        self.name = "remove conflict packages"

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

        for pkg in conflict_pkgs + reinstall_pkgs:
            subprocess.check_call(["rpm", "-e", "--nodeps"] + pkg)

        with open("/etc/leapp/transaction/to_install", "a") as leapp_installation_list:
            for pkg in reinstall_pkgs:
                leapp_installation_list.write(pkg)

    def _post_action(self):
        # Conflict packages shouldn't be reinstalled after a convertation because new once from
        # Alma repositories will be installed instead of them. The exception of it is a psa-mod_proxy,
        # that not needed at all, because the httpd package in new distros brings appropriate apache modules by itself.
        # Packages from the reinstall list will be installed by leapp.
        pass

class CheckRemove(Action):
    def __init__(self):
        self.name = "check Remove"

    def _prepare_action(self):
        print("Remove")

    def _post_action(self):
        print("back Remove")