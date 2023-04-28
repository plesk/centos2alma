# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import itertools
import os
import shutil
import subprocess

from common import util, log


def extract_repodata(repofile):
    id = None
    name = None
    url = None
    metalink = None
    additional = []

    with open(repofile, "r") as repo:
        for line in repo.readlines():
            if line.startswith("["):
                if id is not None:
                    yield (id, name, url, metalink, additional)

                id = None
                name = None
                url = None
                metalink = None
                additional = []

            log.debug("Repository file line: {line}".format(line=line.rstrip()))
            if line.startswith("["):
                id = line[1:-2]
                continue

            if "=" not in line:
                additional.append(line)
                continue

            field, val = line.split("=", 1)
            field = field.strip().rstrip()
            val = val.strip().rstrip()
            if field == "name":
                name = val
            elif field == "baseurl":
                url = val
            elif field == "metalink":
                metalink = val
            else:
                additional.append(line)

    yield (id, name, url, metalink, additional)


def remove_repositories(repofile, repositories):
    with open(repofile, "r") as original, open(repofile + ".next", "w") as dst:
        inRepo = False
        for line in original.readlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                if line[1:-1] in repositories:
                    inRepo = True
                else:
                    inRepo = False

            if not inRepo:
                dst.write(line + "\n")

    shutil.move(repofile + ".next", repofile)


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
