# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction

import os

from common import leapp_configs, files


class LeapReposConfiguration(ActiveAction):

    def __init__(self):
        self.name = "map plesk repositories for leapp"

    def _prepare_action(self):
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*.repo", "epel.repo"])

        leapp_configs.add_repositories_mapping(repofiles, ignore=[
            "PLESK_17_PHP52", "PLESK_17_PHP53", "PLESK_17_PHP54",
            "PLESK_17_PHP55", "PLESK_17_PHP56", "PLESK_17_PHP70",
        ])

    def _post_action(self):
        # Since only leap related files should be changed, there is no to do after a conversation
        pass

    def _revert_action(self):
        pass


class LeapChoicesConfiguration(ActiveAction):

    def __init__(self):
        self.name = "configure leapp user choices"

    def _prepare_action(self):
        with open('/var/log/leapp/answerfile.userchoices', 'w') as usercoise:
            usercoise.write("[remove_pam_pkcs11_module_check]\nconfirm = True\n")

    def _post_action(self):
        # Since only leap related files should be changed, there is no to do after a conversation
        pass

    def _revert_action(self):
        pass


class PatchLeappErrorOutput(ActiveAction):

    def __init__(self):
        self.name = "patch leapp error log output"
        self.path_to_src = "/usr/share/leapp-repository/repositories/system_upgrade/common/libraries/dnfplugin.py"

    def _prepare_action(self):
        # Looks like there is no setter for stdout/stderr in the python for leapp
        files.replace_string(self.path_to_src, "if six.PY2:", "if False:")

    def _post_action(self):
        pass

    def _revert_action(self):
        pass