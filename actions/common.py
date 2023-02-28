from .action import ActiveAction, CheckAction

import os
import subprocess
import sys

import common
from common import util


class FixNamedConfig(ActiveAction):
    def __init__(self):
        self.name = "fix named configuration"
        self.user_options_path = "/etc/named-user-options.conf"

    def _prepare_action(self):
        if not os.path.exists(self.user_options_path):
            os.symlink("/var/named/chroot/etc/named-user-options.conf", self.user_options_path)

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
        return common.is_package_installed("psa-spamassassin")

    def _prepare_action(self):
        util.logged_check_call(["systemctl", "stop", "spamassassin.service"])
        util.logged_check_call(["systemctl", "disable", "spamassassin.service"])

    def _post_action(self):
        util.logged_check_call(["plesk", "sbin", "spammng", "--enable"])
        util.logged_check_call(["plesk", "sbin", "spammng", "--update", "--enable-server-configs", "--enable-user-configs"])

        util.logged_check_call(["systemctl", "daemon-reload"])
        util.logged_check_call(["systemctl", "enable", "spamassassin.service"])

    def _revert_action(self):
        util.logged_check_call(["systemctl", "enable", "spamassassin.service"])
        util.logged_check_call(["systemctl", "start", "spamassassin.service"])


class DisableSuspiciousKernelModules(ActiveAction):
    def __init__(self):
        self.name = "rule suspicious kernel modules"
        self.suspicious_modules = ["pata_acpi", "btrfs", "floppy"]
        self.modules_konfig_path = "/etc/modprobe.d/pataacpibl.conf"

    def _get_enabled_modules(self, lookup_modules):
        modules = []
        process = subprocess.run(["lsmod"], stdout=subprocess.PIPE, universal_newlines=True)
        for line in process.stdout.splitlines():
            module_name = line[:line.find(' ')]
            if module_name in lookup_modules:
                modules.append(module_name)
        return modules

    def _prepare_action(self):
        with open(self.modules_konfig_path, "a") as kern_mods_config:
            for suspicious_module in self.suspicious_modules:
                kern_mods_config.write("blacklist {module}\n".format(module=suspicious_module))

        for enabled_modules in self._get_enabled_modules(self.suspicious_modules):
            util.logged_check_call(["rmmod", enabled_modules])

    def _post_action(self):
        for module in self.suspicious_modules:
            common.replace_string(self.modules_konfig_path, "blacklist " + module, "")

    def _revert_action(self):
        for module in self.suspicious_modules:
            common.replace_string(self.modules_konfig_path, "blacklist " + module, "")


class RuleSelinux(ActiveAction):
    def __init__(self):
        self.name = "rule selinux status"
        self.selinux_config = "/etc/selinux/config"

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
Message from Plesk distupgrade tool:
Congratulations! Your instance has been successfully converted into AlmaLinux8.
Please remove this message from /etc/motd file.
===============================================================================
"""

    def _prepare_action(self):
        pass

    def _post_action(self):
        common.restore_file_from_backup(self.motd_path)

        with open(self.motd_path, "a") as motd:
            motd.write(self.finish_message)

    def _revert_action(self):
        pass


class AddInProgressSshLoginMessage(ActiveAction):
    def __init__(self):
        self.name = "add in progress ssh login message"
        self.motd_path = "/etc/motd"
        path_to_script = os.path.abspath(sys.argv[0])
        self.in_progress_message = f"""
===============================================================================
Message from Plesk distupgrade tool:
Your instance is being converted into AlmaLinux8. Please wait until the script
finish last preparations and reboot the instance.
You could check the progress by running '{path_to_script} --status' command
or monitor progress with '{path_to_script} --monitor' command.
===============================================================================
"""

    def _prepare_action(self):
        common.backup_file(self.motd_path)

        with open(self.motd_path, "a") as motd:
            motd.write(self.in_progress_message)

    def _post_action(self):
        pass

    def _revert_action(self):
        common.restore_file_from_backup(self.motd_path)


class PleskInstallerNotInProgress(CheckAction):
    def __init__(self):
        self.name = "checking if Plesk installer is in progress"
        self.description = "Plesk installer is in progress. Please wait until it is finished. Or use 'plesk installer stop' to abort it."

    def _do_check(self):
        installer_check = subprocess.run(["plesk", "installer", "--query-status", "--enable-xml-output"], stdout=subprocess.PIPE, universal_newlines=True)
        if "query_ok" in installer_check.stdout:
            return True
        return False
