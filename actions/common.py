from .action import Action

import os
import subprocess


class FixNamedConfig(Action):
    def __init__(self):
        self.name = "fix named configuration"

    def _prepare_action(self):
        os.symlink("/var/named/chroot/etc/named-user-options.conf", "/etc/named-user-options.conf")

    def _post_action(self):
        os.unlink("/etc/named-user-options.conf")


class DisableSuspiciousKernelModules(Action):
    def __init__(self):
        self.name = "rule suspicious kernel modules"
        self.suspicious_modules = ["pata_acpi", "btrfs"]
        self.modules_konfig_path = "/etc/modprobe.d/pataacpibl.conf"

    def _prepare_action(self):
        with open(self.modules_konfig_path, "a") as kern_mods_config:
            for module in self.suspicious_modules:
                kern_mods_config.write("blacklist {module}\n".format(module))

            subprocess.check_call(["rmmod", module])

    def _post_action(self):
        for module in self.suspicious_modules:
            self._replace_string(self.modules_konfig_path, "blacklist " + module, "")


class RuleSelinux(Action):
    def __init__(self):
        self.name = "rule selinux status"
        self.selinux_config = "/etc/selinux/config"

    def _prepare_action(self):
        self._replace_string(self.selinux_config, "SELINUX=enforcing", "SELINUX=permissive")

    def _post_action(self):
        self._replace_string(self.selinux_config, "SELINUX=permissive", "SELINUX=enforcing")


class CheckCommon(Action):
    def __init__(self):
        self.name = "check 1"

    def _prepare_action(self):
        print("common")

    def _post_action(self):
        print("back common")