# Copyright 1999 - 2024. Plesk International GmbH. All rights reserved.
import os

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
            "PLESK_17_PHP52", "PLESK_17_PHP53", "PLESK_17_PHP54",
            "PLESK_17_PHP55", "PLESK_17_PHP56", "PLESK_17_PHP70",
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


class PatchLeappErrorOutput(action.ActiveAction):

    def __init__(self):
        self.name = "patch leapp error log output"
        self.path_to_src = "/usr/share/leapp-repository/repositories/system_upgrade/common/libraries/dnfplugin.py"

    def _prepare_action(self) -> action.ActionResult:
        # Looks like there is no setter for stdout/stderr in the python for leapp
        files.replace_string(self.path_to_src, "if six.PY2:", "if False:")
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class PatchLeappDebugNonAsciiPackager(action.ActiveAction):

    def __init__(self):
        self.name = "patch leapp to allow print debug message for non-ascii packager"
        self.path_to_src = "/usr/share/leapp-repository/repositories/system_upgrade/common/actors/redhatsignedrpmscanner/actor.py"

    def is_required(self) -> bool:
        return os.path.exists(self.path_to_src)

    def _prepare_action(self) -> action.ActionResult:
        # so sometimes we could have non-ascii packager name, in this case leapp will fail
        # on printing debug message. So we need to encode it to utf-8 before print (and only before print I think)
        files.replace_string(self.path_to_src, ", pkg.packager", ", pkg.packager.encode('utf-8')")
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class PatchLeappHandleDnfpluginErrorAscii(action.ActiveAction):
    path_to_src: str

    def __init__(self):
        self.name = "patch leapp to handle dnf plugin error for ascii packager"
        self.path_to_src = "/usr/share/leapp-repository/repositories/system_upgrade/common/libraries/dnfplugin.py"

    def is_required(self) -> bool:
        return os.path.exists(self.path_to_src)

    def _prepare_action(self) -> action.ActionResult:
        files.replace_string(self.path_to_src, "if False", "if True")
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()
