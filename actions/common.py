from .action import ActiveAction

import os
import subprocess

import common


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


class FixSpamassassinConfig(ActiveAction):
    # Make sure the trick is preformed before any call of 'systemctl daemon-reload'
    # because we change spamassassin.service configuration in scope of this action.
    def __init__(self):
        self.name = "fix spamassassin configuration"
        self.spamassassin_config_path = "/etc/mail/spamassassin/local.cf"

    def _prepare_action(self):
        pass

    def _post_action(self):
        subprocess.check_call(["plesk", "sbin", "spammng", "--enable"])
        subprocess.check_call(["plesk", "sbin", "spammng", "--update", "--enable-server-configs", "--enable-user-configs"])


class DisableSuspiciousKernelModules(ActiveAction):
    def __init__(self):
        self.name = "rule suspicious kernel modules"
        self.suspicious_modules = ["pata_acpi", "btrfs"]
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
            subprocess.check_call(["rmmod", enabled_modules])

    def _post_action(self):
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


class FinishMessage(ActiveAction):
    def __init__(self):
        self.name = "printing congratulations"

    def _prepare_action(self):
        pass

    def _post_action(self):
        common.log.info("Done! Your instance has been converted into AlmaLinux8.")
