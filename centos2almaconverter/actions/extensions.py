# Copyright 1999 - 2025. Plesk International GmbH. All rights reserved.
import os

from pleskdistup import actions as common_actions
from pleskdistup.common import action, util, leapp_configs, files, rpm


class FixupImunify(action.ActiveAction):
    def __init__(self):
        self.name = "fixing up imunify360"

    def _is_required(self) -> bool:
        return len(files.find_files_case_insensitive("/etc/yum.repos.d", ["imunify*.repo"])) > 0

    def _prepare_action(self) -> action.ActionResult:
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["imunify*.repo"])

        leapp_configs.add_repositories_mapping(repofiles)

        if "/etc/yum.repos.d/imunify360-alt-php.repo" in repofiles:
            # The alt-php repository uses gpg key protected by password authentication,
            # so since we have no way to pass the credentials to Leapp,
            # we need to extract gpg key from rpm database and use it instead.
            rpm.extract_gpgkey_from_rpm_database(".*CloudLinux.*", "/etc/leapp/files/vendors.d/rpm-gpg/RPM-GPG-KEY-CloudLinux")
            files.replace_string(
                "/etc/leapp/files/leapp_upgrade_repositories.repo",
                "gpgkey=http://repo.alt.cloudlinux.com/el/alt-php/install/centos/RPM-GPG-KEY-CloudLinux",
                "gpgkey=file:///etc/leapp/files/vendors.d/rpm-gpg/RPM-GPG-KEY-CloudLinux"
            )

        # libssh2 and libunwind are needed for imunify360, so we must configure actions for them.
        # We need to map the packages to the ones available in the AlmaLinux 8 EPEL repository.
        # Additionally, we must remove the actions for libssh2 from the sl repo and
        # libunwind from the appstream repo. For some reason, leapp checks all actions
        # and becomes confused by these actions.
        leapp_configs.set_package_mapping("libssh2", "base", "libssh2", "el8-epel")
        leapp_configs.remove_package_action("libssh2", "sl")

        leapp_configs.set_package_action("libunwind", leapp_configs.LeappActionType.REPLACED)
        leapp_configs.set_package_mapping("libunwind", "base", "libunwind", "el8-epel")
        leapp_configs.remove_package_action("libunwind", "almalinux8-appstream")
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


class FetchKernelCareGPGKey(common_actions.FetchGPGKeyForLeapp):
    def __init__(self):
        self.name = "fetching KernelCare GPG key"
        self.target_repository_files_regex = ["kernelcare*.repo"]
        super().__init__()


class FetchPleskGPGKey(common_actions.FetchGPGKeyForLeapp):
    def __init__(self):
        self.name = "fetching Plesk GPG key"
        self.target_repository_files_regex = ["plesk*.repo"]
        super().__init__()


class FetchImunifyGPGKey(common_actions.FetchGPGKeyForLeapp):
    def __init__(self):
        self.name = "fetching Imunify360 GPG key"
        self.target_repository_files_regex = ["imunify*.repo"]
        super().__init__()
