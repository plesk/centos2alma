# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction

import os
import subprocess
import sys

import common
from common import log, util, rpm


class FixNamedConfig(ActiveAction):
    def __init__(self):
        self.name = "fix named configuration"
        self.user_options_path = "/etc/named-user-options.conf"
        self.chrooted_file_path = "/var/named/chroot/etc/named-user-options.conf"

    def _is_required(self):
        return os.path.exists(self.chrooted_file_path)

    def _prepare_action(self):
        if not os.path.exists(self.user_options_path):
            os.symlink(self.chrooted_file_path, self.user_options_path)

    def _post_action(self):
        if os.path.exists(self.user_options_path):
            os.unlink(self.user_options_path)

    def _revert_action(self):
        if os.path.exists(self.user_options_path):
            os.unlink(self.user_options_path)


class FixSpamassassinConfig(ActiveAction):
    # Make sure the trick is preformed before any call of 'systemctl daemon-reload'
    # because we change spamassassin.service configuration in scope of this action.
    def __init__(self):
        self.name = "fix spamassassin configuration"

    def _is_required(self):
        return rpm.is_package_installed("psa-spamassassin")

    def _prepare_action(self):
        util.logged_check_call(["/usr/bin/systemctl", "stop", "spamassassin.service"])
        util.logged_check_call(["/usr/bin/systemctl", "disable", "spamassassin.service"])

    def _post_action(self):
        util.logged_check_call(["/usr/sbin/plesk", "sbin", "spammng", "--enable"])
        util.logged_check_call(["/usr/sbin/plesk", "sbin", "spammng", "--update", "--enable-server-configs", "--enable-user-configs"])

        util.logged_check_call(["/usr/bin/systemctl", "daemon-reload"])
        util.logged_check_call(["/usr/bin/systemctl", "enable", "spamassassin.service"])

    def _revert_action(self):
        util.logged_check_call(["/usr/bin/systemctl", "enable", "spamassassin.service"])
        util.logged_check_call(["/usr/bin/systemctl", "start", "spamassassin.service"])


class DisableSuspiciousKernelModules(ActiveAction):
    def __init__(self):
        self.name = "rule suspicious kernel modules"
        self.suspicious_modules = ["pata_acpi", "btrfs", "floppy"]
        self.modules_konfig_path = "/etc/modprobe.d/pataacpibl.conf"

    def _get_enabled_modules(self, lookup_modules):
        modules = []
        modules_list = subprocess.check_output(["/usr/sbin/lsmod"], universal_newlines=True).splitlines()
        for line in modules_list:
            module_name = line[:line.find(' ')]
            if module_name in lookup_modules:
                modules.append(module_name)
        return modules

    def _prepare_action(self):
        with open(self.modules_konfig_path, "a") as kern_mods_config:
            for suspicious_module in self.suspicious_modules:
                kern_mods_config.write("blacklist {module}\n".format(module=suspicious_module))

        for enabled_modules in self._get_enabled_modules(self.suspicious_modules):
            util.logged_check_call(["/usr/sbin/rmmod", enabled_modules])

    def _post_action(self):
        for module in self.suspicious_modules:
            common.replace_string(self.modules_konfig_path, "blacklist " + module, "")

    def _revert_action(self):
        if not os.path.exists(self.modules_konfig_path):
            return

        for module in self.suspicious_modules:
            common.replace_string(self.modules_konfig_path, "blacklist " + module, "")


class RuleSelinux(ActiveAction):
    def __init__(self):
        self.name = "rule selinux status"
        self.selinux_config = "/etc/selinux/config"

    def _is_required(self):
        return os.path.exists(self.selinux_config)

    def _prepare_action(self):
        common.replace_string(self.selinux_config, "SELINUX=enforcing", "SELINUX=permissive")

    def _post_action(self):
        common.replace_string(self.selinux_config, "SELINUX=permissive", "SELINUX=enforcing")

    def _revert_action(self):
        common.replace_string(self.selinux_config, "SELINUX=permissive", "SELINUX=enforcing")


class AddFinishSshLoginMessage(ActiveAction):
    def __init__(self):
        self.name = "add finish ssh login message"
        self.motd_path = "/etc/motd"
        self.finish_message = """
===============================================================================
Message from Plesk centos2alma tool:
The server has been converted to AlmaLinux 8.
You can remove this message from the /etc/motd file.
===============================================================================
"""

    def _prepare_action(self):
        pass

    def _post_action(self):
        try:
            common.restore_file_from_backup(self.motd_path, remove_if_no_backup=True)

            with open(self.motd_path, "a") as motd:
                motd.write(self.finish_message)
        except FileNotFoundError:
            common.log.warn("The /etc/motd file cannot be changed or created. The script may be lacking the permissions to do so.")
            pass

    def _revert_action(self):
        pass


class AddInProgressSshLoginMessage(ActiveAction):
    def __init__(self):
        self.name = "add in progress ssh login message"
        self.motd_path = "/etc/motd"
        path_to_script = os.path.abspath(sys.argv[0])
        self.in_progress_message = f"""
===============================================================================
Message from the Plesk centos2alma tool:
The server is being converted to AlmaLinux 8. Please wait.
To see the current conversion status, run the '{path_to_script} --status' command.
To monitor the conversion progress in real time, run the '{path_to_script} --monitor' command.
===============================================================================
"""

    def _prepare_action(self):
        try:
            common.backup_file(self.motd_path)

            with open(self.motd_path, "a") as motd:
                motd.write(self.in_progress_message)
        except FileNotFoundError:
            log.warn("The /etc/motd file cannot be changed or created. The script may be lacking the permissions to do so.")
            pass

    def _post_action(self):
        pass

    def _revert_action(self):
        common.restore_file_from_backup(self.motd_path, remove_if_no_backup=True)


class DisablePleskSshBanner(ActiveAction):
    def __init__(self):
        self.name = "disable plesk ssh banner"
        self.banner_command_path = "/root/.plesk_banner"

    def _prepare_action(self):
        if os.path.exists(self.banner_command_path):
            common.backup_file(self.banner_command_path)
            os.unlink(self.banner_command_path)

    def _post_action(self):
        common.restore_file_from_backup(self.banner_command_path)

    def _revert_action(self):
        common.restore_file_from_backup(self.banner_command_path)
