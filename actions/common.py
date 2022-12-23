from .action import ActivaAction

import os
import subprocess

import common


class FixNamedConfig(ActivaAction):
    def __init__(self):
        self.name = "fix named configuration"
        self.user_options_path = "/etc/named-user-options.conf"

    def _prepare_action(self):
        if not os.path.exists(self.user_options_path):
            os.symlink("/var/named/chroot/etc/named-user-options.conf", self.user_options_path)

    def _post_action(self):
        if os.path.exists(self.user_options_path):
            os.unlink(self.user_options_path)


class DisableSuspiciousKernelModules(ActivaAction):
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
            self._replace_string(self.modules_konfig_path, "blacklist " + module, "")


class RuleSelinux(ActivaAction):
    def __init__(self):
        self.name = "rule selinux status"
        self.selinux_config = "/etc/selinux/config"

    def _prepare_action(self):
        self._replace_string(self.selinux_config, "SELINUX=enforcing", "SELINUX=permissive")

    def _post_action(self):
        self._replace_string(self.selinux_config, "SELINUX=permissive", "SELINUX=enforcing")


class FinishMessage(ActivaAction):
    def __init__(self):
        self.name = "rule selinux status"

    def _prepare_action(self):
        pass

    def _post_action(self):
        common.log.info("Hooray! Your instance has been converted into AlmaLinux8.\nPlease reboot the instance to startup plesk services")
