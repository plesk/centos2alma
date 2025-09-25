# Copyright 1999 - 2025. Plesk International GmbH. All rights reserved.
import os
import shutil

from pleskdistup.common import action, leapp_configs, files


class PrepareLeappConfigurationBackup(action.ActiveAction):
    def __init__(self):
        self.name = "prepare leapp configuration backup"
        self.leapp_configs = ["/etc/leapp/files/leapp_upgrade_repositories.repo",
                              "/etc/leapp/files/repomap.csv",
                              "/etc/leapp/files/pes-events.json"]

    def _prepare_action(self) -> action.ActionResult:
        for file in self.leapp_configs:
            if os.path.exists(file):
                files.backup_file(file)

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for file in self.leapp_configs:
            if os.path.exists(file):
                files.remove_backup(file)

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for file in self.leapp_configs:
            if os.path.exists(file):
                files.restore_file_from_backup(file)

        return action.ActionResult()


class LeapReposConfiguration(action.ActiveAction):

    def __init__(self):
        self.name = "map plesk repositories for leapp"

    def _prepare_action(self) -> action.ActionResult:
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*.repo", "epel.repo"])

        leapp_configs.add_repositories_mapping(repofiles, ignore=[
            "PLESK_17_PHP52", "PLESK_17_PHP53", "PLESK_17_PHP54", "PLESK_17_PHP55",
        ])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        # Since only leap related files should be changed, there is nothing to do after on finishing stage
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class LeapChoicesConfiguration(action.ActiveAction):

    def __init__(self):
        self.name = "configure leapp user choices"
        self.answer_file_path = "/var/log/leapp/answerfile.userchoices"

    def _prepare_action(self) -> action.ActionResult:
        try:
            with open(self.answer_file_path, 'w') as usercoise:
                usercoise.write("[remove_pam_pkcs11_module_check]\nconfirm = True\n")
        except FileNotFoundError:
            raise RuntimeError("Unable to create the leapp user answer file '{}'. Likely the script does not have "
                               "sufficient permissions to write in this directory. Please run the script as root "
                               "and use `setenforce 0` to disable selinux".format(self.answer_file_path))

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        if os.path.exists(self.answer_file_path):
            os.unlink(self.answer_file_path)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class UseSystemResolveForLeappContainer(action.ActiveAction):
    path_to_src: str

    def __init__(self) -> None:
        self.name = "configure leapp container to use host's /etc/resolv.conf"
        self.path_to_resolve = "/etc/resolv.conf"
        self.path_to_src = "/etc/leapp/files/resolv.conf"

    def is_required(self) -> bool:
        return os.path.exists(self.path_to_resolve)

    def _prepare_action(self) -> action.ActionResult:
        shutil.copy(self.path_to_resolve, self.path_to_src)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()
