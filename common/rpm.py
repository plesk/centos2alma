# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import subprocess

from common import util


def filter_installed_packages(lookup_pkgs):
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


def is_package_installed(pkg):
    res = subprocess.run(["rpm", "--quiet", "--query", pkg])
    return res.returncode == 0


def install_packages(pkgs):
    util.logged_check_call(["yum", "install", "-y"] + pkgs)


def remove_packages(pkgs):
    util.logged_check_call(["rpm", "-e", "--nodeps"] + pkgs)
