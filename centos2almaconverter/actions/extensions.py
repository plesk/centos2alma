# Copyright 1999 - 2024. Plesk International GmbH. All rights reserved.
from pleskdistup.common import action, util, leapp_configs, files


class FixupImunify(action.ActiveAction):
    def __init__(self):
        self.name = "fixing up imunify360"

    def _is_required(self) -> bool:
        return len(files.find_files_case_insensitive("/etc/yum.repos.d", ["imunify*.repo"])) > 0

    def _prepare_action(self) -> action.ActionResult:
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["imunify*.repo"])

        leapp_configs.add_repositories_mapping(repofiles)

        # For some reason leapp replaces the libssh2 package on installation. It's fine in most cases,
        # but imunify packages require libssh2. So we should use PRESENT action to keep it.
        leapp_configs.set_package_action("libssh2", leapp_configs.LeappActionType.PRESENT)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class AdoptKolabRepositories(action.ActiveAction):
    def __init__(self):
        self.name = "adopting kolab repositories"

    def _is_required(self) -> bool:
        return len(files.find_files_case_insensitive("/etc/yum.repos.d", ["kolab*.repo"])) > 0

    def _prepare_action(self) -> action.ActionResult:
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["kolab*.repo"])

        leapp_configs.add_repositories_mapping(repofiles, ignore=["kolab-16-source",
                                                                  "kolab-16-testing-source",
                                                                  "kolab-16-testing-candidate-source"])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["kolab*.repo"]):
            leapp_configs.adopt_repositories(file)

        util.logged_check_call(["/usr/bin/dnf", "-y", "update"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 30

    def estimate_post_time(self) -> int:
        return 2 * 60
