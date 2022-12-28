import os
import json

import common

# class LeappConfig():

PATH_TO_CONFIGFILES = "/etc/leapp/files"
LEAPP_REPOS_FILE_PATH = os.path.join(PATH_TO_CONFIGFILES, "leapp_upgrade_repositories.repo")
LEAPP_MAP_FILE_PATH = os.path.join(PATH_TO_CONFIGFILES, "repomap.csv")

REPO_HEAD_FORMAT = """
[{id}]
name={name}
baseurl={url}
"""


def _do_replacement(to_change, replacement_list):
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
    additional = []

    with open(repofile, "r") as repo:
        for line in repo.readlines():
            if line.startswith("["):
                if id is not None:
                    yield (id, name, url, additional)

                id = None
                name = None
                url = None
                additional = []

            if line.startswith("["):
                id = line[1:-2]
            elif line.startwith("name="):
                name = line[5:].rstrip()
            elif line.startwith("baseurl="):
                url = line[8:].rstrip()
            else:
                additional.append(line)

    yield (id, name, url, additional)


def add_repositories_mapping(repofiles):
    with open(LEAPP_REPOS_FILE_PATH, "a") as leapp_repos_file, open(LEAPP_MAP_FILE_PATH, "a") as map_file:
        for file in repofiles:
            if not os.path.exists(file):
                common.log.warn("The repository mapper has tried to open an unexsisted file: {filename}".format(filename=file))
                continue

            for id, name, url, additional_lines in _extract_repodata(file):
                if name is None or url is None:
                    common.log.warn("Repository info with id '{}' from the repofile '{}' don't have a name or baseurl".format(id, file))

                new_id = _do_id_replacement(id)
                name = _do_name_replacement(name)
                url = _do_url_replacement(url)

                leapp_repos_file.write(REPO_HEAD_FORMAT.format(id=new_id, name=name, url=url))
                for line in [_do_common_replacment(add_line) for add_line in additional_lines]:
                    leapp_repos_file.write(line)

                # Special case for plesk repository. We need to add dist repository to install some of plesk packages
                if id.startswith("PLESK_18_0") and "extras" in line:
                    leapp_repos_file.write(REPO_HEAD_FORMAT.format(id=new_id.replace("-extras", ""),
                                                                   name=name.replace("-extras", ""),
                                                                   url=url.replace("extras", "dist")))
                    leapp_repos_file.write("enabled=1\ngpgcheck=1\n")

                map_file.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=id, newrepo=new_id))

