# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import os
import json
import shutil

from enum import IntEnum

import common


PATH_TO_CONFIGFILES = "/etc/leapp/files"
LEAPP_REPOS_FILE_PATH = os.path.join(PATH_TO_CONFIGFILES, "leapp_upgrade_repositories.repo")
LEAPP_MAP_FILE_PATH = os.path.join(PATH_TO_CONFIGFILES, "repomap.csv")
LEAPP_PKGS_CONF_PATH = os.path.join(PATH_TO_CONFIGFILES, "pes-events.json")

REPO_HEAD_WITH_URL = """
[{id}]
name={name}
baseurl={url}
"""

REPO_HEAD_WITH_METALINK = """
[{id}]
name={name}
metalink={url}
"""


def _do_replacement(to_change, replacement_list):
    if to_change is None:
        return None

    for replace in replacement_list:
        to_change = replace(to_change)
    return to_change


def _do_id_replacement(id):
    return _do_replacement(id, [
        lambda to_change: "alma-" + to_change,
    ])


def _do_name_replacement(name):
    return _do_replacement(name, [
        lambda to_change: "Alma " + to_change,
        lambda to_change: to_change.replace("Enterprise Linux 7",  "Enterprise Linux 8"),
        lambda to_change: to_change.replace("EPEL-7", "EPEL-8"),
        lambda to_change: to_change.replace("$releasever", "8"),
    ])


def _fixup_old_php_urls(to_change):
    supported_old_versions = ["7.1", "7.2", "7.3"]
    for version in supported_old_versions:
        if "PHP_" + version in to_change:
            return to_change.replace("rpm-CentOS-7", "rpm-CentOS-8")

    return to_change


def _do_url_replacement(url):
    return _do_replacement(url, [
        _fixup_old_php_urls,
        lambda to_change: to_change.replace("rpm-CentOS-7", "rpm-RedHat-el8"),
        lambda to_change: to_change.replace("epel-7", "epel-8"),
        lambda to_change: to_change.replace("epel-debug-7", "epel-debug-8"),
        lambda to_change: to_change.replace("epel-source-7", "epel-source-8"),
        lambda to_change: to_change.replace("centos7", "centos8"),
        lambda to_change: to_change.replace("centos/7", "centos/8"),
        lambda to_change: to_change.replace("rhel/7", "rhel/8"),
        lambda to_change: to_change.replace("CentOS_7", "CentOS_8"),
        lambda to_change: to_change.replace("rhel-$releasever", "rhel-8"),
        lambda to_change: to_change.replace("$releasever", "8"),
        lambda to_change: to_change.replace("autoinstall.plesk.com/PMM_0.1.10", "autoinstall.plesk.com/PMM_0.1.11"),
        lambda to_change: to_change.replace("autoinstall.plesk.com/PMM0", "autoinstall.plesk.com/PMM_0.1.11"),
    ])


def _do_common_replacement(line):
    return _do_replacement(line, [
        lambda to_change: to_change.replace("EPEL-7", "EPEL-8"),
        # We can't check repository gpg because the key is not stored in the temporary file system
        # ToDo: Maybe we could find a way to put the key into the file system
        lambda to_change: to_change.replace("repo_gpgcheck = 1", "repo_gpgcheck = 0"),
    ])


def _extract_repodata(repofile):
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

            common.log.debug("Repository file line: {line}".format(line=line.rstrip()))
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


def is_repo_ok(id, name, url, metalink):
    if name is None:
        common.log.warn("Repository info for '[{id}]' has no a name".format(id=id))
        return False

    if url is None and metalink is None:
        common.log.warn("Repository info for '{id}' has no baseurl and metalink".format(id=id))
        return False

    return True


def adopt_repositories(repofile, ignore=None):
    if ignore is None:
        ignore = []

    common.log.debug("Adopt repofile '{filename}' for AlmaLinux 8".format(filename=repofile))

    if not os.path.exists(repofile):
        common.log.warn("The repository adapter has tried to open an unexistent file: {filename}".format(filename=repofile))
        return

    with open(repofile + ".next", "a") as dst:
        for id, name, url, metalink, additional_lines in _extract_repodata(repofile):
            if not is_repo_ok(id, name, url, metalink):
                continue

            if id in ignore:
                common.log.debug("Skip repository '{id}' adaptation since it is in ignore list.".format(id=id))
                continue

            common.log.debug("Adopt repository with id '{id}' is extracted.".format(id=id))

            id = _do_id_replacement(id)
            name = _do_name_replacement(name)
            if url is not None:
                url = _do_url_replacement(url)
                repo_format = REPO_HEAD_WITH_URL
            else:
                url = _do_url_replacement(metalink)
                repo_format = REPO_HEAD_WITH_METALINK

            dst.write(repo_format.format(id=id, name=name, url=url))

            for line in (_do_common_replacement(add_line) for add_line in additional_lines):
                dst.write(line)

    shutil.move(repofile + ".next", repofile)


def add_repositories_mapping(repofiles, ignore=None, leapp_repos_file_path=LEAPP_REPOS_FILE_PATH, mapfile_path=LEAPP_MAP_FILE_PATH):
    if ignore is None:
        ignore = []

    with open(leapp_repos_file_path, "a") as leapp_repos_file, open(mapfile_path, "a") as map_file:
        for file in repofiles:
            common.log.debug("Processing repofile '{filename}' into leapp configuration".format(filename=file))

            if not os.path.exists(file):
                common.log.warn("The repository mapper has tried to open an unexistent file: {filename}".format(filename=file))
                continue

            for id, name, url, metalink, additional_lines in _extract_repodata(file):
                if not is_repo_ok(id, name, url, metalink):
                    continue

                if id in ignore:
                    common.log.debug("Skip repository '{id}' since it is in ignore list.".format(id=id))
                    continue

                common.log.debug("Repository entry with id '{id}' is extracted.".format(id=id))

                new_id = _do_id_replacement(id)
                name = _do_name_replacement(name)
                if url is not None:
                    url = _do_url_replacement(url)
                    repo_format = REPO_HEAD_WITH_URL
                else:
                    url = _do_url_replacement(metalink)
                    repo_format = REPO_HEAD_WITH_METALINK

                leapp_repos_file.write(repo_format.format(id=new_id, name=name, url=url))

                for line in (_do_common_replacement(add_line) for add_line in additional_lines):
                    leapp_repos_file.write(line)

                # Special case for plesk repository. We need to add dist repository to install some of plesk packages
                # We support metalink for plesk repository, regardless of the fact we don't use them now
                if id.startswith("PLESK_18_0") and "extras" in id and url is not None:
                    leapp_repos_file.write(repo_format.format(id=new_id.replace("-extras", ""),
                                                              name=name.replace("extras", ""),
                                                              url=url.replace("extras", "dist")))
                    leapp_repos_file.write("enabled=1\ngpgcheck=1\n")

                    map_file.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=id, newrepo=new_id.replace("-extras", "")))

                leapp_repos_file.write("\n")

                map_file.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=id, newrepo=new_id))

        map_file.write("\n")


def set_package_repository(package, repository, leapp_pkgs_conf_path=LEAPP_PKGS_CONF_PATH):
    pkg_mapping = None
    with open(leapp_pkgs_conf_path, "r") as pkg_mapping_file:
        pkg_mapping = json.load(pkg_mapping_file)
        for info in pkg_mapping["packageinfo"]:
            for outpkg in info["out_packageset"]["package"]:
                if outpkg["name"] == package:
                    outpkg["repository"] = repository

    common.rewrite_json_file(leapp_pkgs_conf_path, pkg_mapping)


# The following types are defined in the leapp-repository repository and can be used
# to define the action type of the package in the pes-events.json file.
class LeappActionType(IntEnum):
    PRESENT = 0
    REMOVED = 1
    DEPRECATED = 2
    REPLACED = 3
    SPLIT = 4
    MERGED = 5
    MOVED = 6
    RENAMED = 7


def set_package_action(package, type, leapp_pkgs_conf_path=LEAPP_PKGS_CONF_PATH):
    pkg_mapping = None
    with open(leapp_pkgs_conf_path, "r") as pkg_mapping_file:
        pkg_mapping = json.load(pkg_mapping_file)
        for info in pkg_mapping["packageinfo"]:
            for inpackage in info["in_packageset"]["package"]:
                if inpackage["name"] == package:
                    info["action"] = type

    common.rewrite_json_file(leapp_pkgs_conf_path, pkg_mapping)
