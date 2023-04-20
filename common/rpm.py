# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import subprocess

from common import util


def filter_installed_packages(lookup_pkgs):
    return [pkg for pkg in lookup_pkgs if is_package_installed(pkg)]


def is_package_installed(pkg):
    res = subprocess.run(["/usr/bin/rpm", "--quiet", "--query", pkg])
    return res.returncode == 0


def install_packages(pkgs):
    if len(pkgs) == 0:
        return
    util.logged_check_call(["/usr/bin/yum", "install", "-y"] + pkgs)


def remove_packages(pkgs):
    if len(pkgs) == 0:
        return
    util.logged_check_call(["/usr/bin/rpm", "-e", "--nodeps"] + pkgs)
