# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import itertools
import os
import subprocess

from common import util


def filter_installed_packages(lookup_pkgs):
    return [pkg for pkg in lookup_pkgs if is_package_installed(pkg)]


def is_package_installed(pkg):
    res = subprocess.run(["/usr/bin/rpm", "--quiet", "--query", pkg])
    return res.returncode == 0


def install_packages(pkgs, repository=None):
    if len(pkgs) == 0:
        return

    command = ["/usr/bin/yum", "install"]
    if repository is not None:
        command += ["--repo", repository]
    command += ["-y"] + pkgs

    util.logged_check_call(command)


def remove_packages(pkgs):
    if len(pkgs) == 0:
        return

    if os.path.exists("/usr/bin/package-cleanup"):
        duplicates = subprocess.check_output(["/usr/bin/package-cleanup", "--dupes"], universal_newlines=True).splitlines()
        for duplicate, pkg in itertools.product(duplicates, pkgs):
            if pkg in duplicate:
                util.logged_check_call(["/usr/bin/rpm", "-e", "--nodeps", duplicate])
                # Since we removed each duplicate, we don't need to remove the package in the end.
                if pkg in pkgs:
                    pkgs.remove(pkg)

    util.logged_check_call(["/usr/bin/rpm", "-e", "--nodeps"] + pkgs)
