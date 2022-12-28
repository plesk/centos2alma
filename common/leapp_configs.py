import os
import json
import shutil

import common

# class LeappConfig():

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
metalink={link}
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
    ])


def _do_url_replacement(url):
    return _do_replacement(url, [
        lambda to_change: to_change.replace("rpm-CentOS-7", "rpm-RedHat-el8"),
        lambda to_change: to_change.replace("epel-7", "epel-8"),
        lambda to_change: to_change.replace("epel-debug-7", "epel-debug-8"),
        lambda to_change: to_change.replace("epel-source-7", "epel-source-8"),
        lambda to_change: to_change.replace("centos7", "centos8"),
    ])


def _do_common_replacment(line):
    return _do_replacement(line, [
        lambda to_change: to_change.replace("EPEL-7", "EPEL-8"),
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


def add_repositories_mapping(repofiles):
    with open(LEAPP_REPOS_FILE_PATH, "a") as leapp_repos_file, open(LEAPP_MAP_FILE_PATH, "a") as map_file:
        for file in repofiles:
            common.log.debug("Processing repofile '{filename}' into leapp configuration".format(filename=file))

            if not os.path.exists(file):
                common.log.warn("The repository mapper has tried to open an unexsisted file: {filename}".format(filename=file))
                continue

            for id, name, url, metalink, additional_lines in _extract_repodata(file):
                if name is None:
                    common.log.warn("Repository info for '[{id}]' from '{repofile}' has not a name".format(id=id, repofile=file))
                    continue

                if url is None and metalink is None:
                    common.log.warn("Repository info for '{id}' from '{repofile}' has not baseurl and metalink".format(id=id, repofile=file))
                    continue

                common.log.debug("Repository entry with id '{id}' is extracted.".format(id=id))

                new_id = _do_id_replacement(id)
                name = _do_name_replacement(name)
                url = _do_url_replacement(url)
                metalink = _do_url_replacement(metalink)

                if url is not None:
                    leapp_repos_file.write(REPO_HEAD_WITH_URL.format(id=new_id, name=name, url=url))
                else:
                    leapp_repos_file.write(REPO_HEAD_WITH_METALINK.format(id=new_id, name=name, link=metalink))

                for line in [_do_common_replacment(add_line) for add_line in additional_lines]:
                    leapp_repos_file.write(line)

                # Special case for plesk repository. We need to add dist repository to install some of plesk packages
                if id.startswith("PLESK_18_0") and "extras" in line and url is not None:
                    leapp_repos_file.write(REPO_HEAD_WITH_URL.format(id=new_id.replace("-extras", ""),
                                                                     name=name.replace("-extras", ""),
                                                                     url=url.replace("extras", "dist")))
                    leapp_repos_file.write("enabled=1\ngpgcheck=1\n")

                leapp_repos_file.write("\n")

                map_file.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=id, newrepo=new_id))

        map_file.write("\n")


def set_package_repository(package, repository):
    pkg_mapping = None
    with open(LEAPP_PKGS_CONF_PATH, "r") as pkg_mapping_file:
        pkg_mapping = json.load(pkg_mapping_file)
        for info in pkg_mapping["packageinfo"]:
            for outpkg in info["out_packageset"]["package"]:
                if outpkg["name"] == package:
                    outpkg["repository"] = repository

    common.rewrite_json_file(LEAPP_PKGS_CONF_PATH, pkg_mapping)
