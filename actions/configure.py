# Copyright 1999 - 2024. WebPros International GmbH. All rights reserved.
import os

from common import action, leapp_configs, files


class PrepareLeappConfigurationBackup(action.ActiveAction):
    def __init__(self):
        self.name = "prepare leapp configuration backup"
        self.leapp_configs = ["/etc/leapp/files/leapp_upgrade_repositories.repo",
                              "/etc/leapp/files/repomap.csv",
                              "/etc/leapp/files/pes-events.json"]

    def _prepare_action(self) -> None:
        for file in self.leapp_configs:
            if os.path.exists(file):
                files.backup_file(file)

    def _post_action(self) -> None:
        for file in self.leapp_configs:
            if os.path.exists(file):
                files.remove_backup(file)

    def _revert_action(self) -> None:
        for file in self.leapp_configs:
            if os.path.exists(file):
                files.restore_file_from_backup(file)


class LeapReposConfiguration(action.ActiveAction):

    def __init__(self):
        self.name = "map plesk repositories for leapp"

    def _prepare_action(self) -> None:
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*.repo", "epel.repo"])

        leapp_configs.add_repositories_mapping(repofiles, ignore=[
            "PLESK_17_PHP52", "PLESK_17_PHP53", "PLESK_17_PHP54",
            "PLESK_17_PHP55", "PLESK_17_PHP56", "PLESK_17_PHP70",
        ])

    def _post_action(self) -> None:
        # Since only leap related files should be changed, there is nothing to do after on finishing stage
        pass

    def _revert_action(self) -> None:
        pass


class LeapChoicesConfiguration(action.ActiveAction):

    def __init__(self):
        self.name = "configure leapp user choices"
        self.answer_file_path = "/var/log/leapp/answerfile.userchoices"

    def _prepare_action(self) -> None:
        try:
            with open(self.answer_file_path, 'w') as usercoise:
                usercoise.write("[remove_pam_pkcs11_module_check]\nconfirm = True\n")
        except FileNotFoundError:
            raise RuntimeError("Unable to create the leapp user answer file '{}'. Likely the script does not have "
                               "sufficient permissions to write in this directory. Please run the script as root "
                               "and use `setenforce 0` to disable selinux".format(self.answer_file_path))

    def _post_action(self) -> None:
        if os.path.exists(self.answer_file_path):
            os.unlink(self.answer_file_path)

    def _revert_action(self) -> None:
        pass


class PatchLeappErrorOutput(action.ActiveAction):

    def __init__(self):
        self.name = "patch leapp error log output"
        self.path_to_src = "/usr/share/leapp-repository/repositories/system_upgrade/common/libraries/dnfplugin.py"

    def _prepare_action(self) -> None:
        # Looks like there is no setter for stdout/stderr in the python for leapp
        files.replace_string(self.path_to_src, "if six.PY2:", "if False:")

    def _post_action(self) -> None:
        pass

    def _revert_action(self) -> None:
        pass


class PatchLeappDebugNonAsciiPackager(action.ActiveAction):

    def __init__(self):
        self.name = "patch leapp to allow print debug message for non-ascii packager"
        self.path_to_src = "/usr/share/leapp-repository/repositories/system_upgrade/common/actors/redhatsignedrpmscanner/actor.py"

    def is_required(self) -> bool:
        return os.path.exists(self.path_to_src)

    def _prepare_action(self) -> None:
        # so sometimes we could have non-ascii packager name, in this case leapp will fail
        # on printing debug message. So we need to encode it to utf-8 before print (and only before print I think)
        files.replace_string(self.path_to_src, ", pkg.packager", ", pkg.packager.encode('utf-8')")

    def _post_action(self) -> None:
        pass

    def _revert_action(self) -> None:
        pass
