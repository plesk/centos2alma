# Copyright 1999 - 2025. Plesk International GmbH. All rights reserved.
import os
import shutil
import subprocess
import typing

from pleskdistup.common import action, dns, files, log, motd, rpm, util


class FixNamedConfig(action.ActiveAction):
    def __init__(self):
        self.name = "fix named configuration"
        self.named_conf = "/etc/named.conf"
        self.chrooted_configuration_path = "/var/named/chroot"

    def _is_required(self) -> bool:
        return os.path.exists(self.named_conf) and os.path.exists(os.path.join(self.chrooted_configuration_path, self.named_conf))

    def _handle_included_file(self, chrooted_file: str):
        target_file = chrooted_file.replace(self.chrooted_configuration_path, "")

        target_file_directory = os.path.dirname(target_file)
        if not os.path.exists(target_file_directory):
            os.makedirs(target_file_directory)

        if not os.path.exists(target_file):
            if os.path.exists(chrooted_file):
                os.symlink(chrooted_file, target_file)
            else:
                with open(target_file, "w") as _:
                    pass

        if os.path.getsize(target_file) == 0:
            with open(target_file, "w") as f:
                f.write("# centos2alma workaround commentary")

    def _prepare_action(self) -> action.ActionResult:
        for bind_configs in dns.get_all_includes_from_bind_config(self.named_conf, chroot_dir=self.chrooted_configuration_path):
            self._handle_included_file(bind_configs)

        return action.ActionResult()

    def _remove_included_files(self, chrooted_file: str):
        target_file = chrooted_file.replace(self.chrooted_configuration_path, "")
        if os.path.islink(target_file):
            os.unlink(target_file)

    def _post_action(self) -> action.ActionResult:
        for bind_configs in dns.get_all_includes_from_bind_config(self.named_conf, chroot_dir=self.chrooted_configuration_path):
            self._remove_included_files(bind_configs)

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for bind_configs in dns.get_all_includes_from_bind_config(self.named_conf, chroot_dir=self.chrooted_configuration_path):
            self._remove_included_files(bind_configs)

        return action.ActionResult()


class DisableSuspiciousKernelModules(action.ActiveAction):
    def __init__(self):
        self.name = "rule suspicious kernel modules"
        self.suspicious_modules = ["pata_acpi", "btrfs", "floppy"]
        self.modules_konfig_path = "/etc/modprobe.d/pataacpibl.conf"

    def _get_enabled_modules(self, lookup_modules: typing.List[str]) -> typing.List[str]:
        modules = []
        modules_list = subprocess.check_output(["/usr/sbin/lsmod"], universal_newlines=True).splitlines()
        for line in modules_list:
            module_name = line[:line.find(' ')]
            if module_name in lookup_modules:
                modules.append(module_name)
        return modules

    def _prepare_action(self) -> action.ActionResult:
        with open(self.modules_konfig_path, "a") as kern_mods_config:
            for suspicious_module in self.suspicious_modules:
                kern_mods_config.write("blacklist {module}\n".format(module=suspicious_module))

        for enabled_modules in self._get_enabled_modules(self.suspicious_modules):
            util.logged_check_call(["/usr/sbin/rmmod", enabled_modules])

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for module in self.suspicious_modules:
            files.replace_string(self.modules_konfig_path, "blacklist " + module, "")

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        if not os.path.exists(self.modules_konfig_path):
            return action.ActionResult()

        for module in self.suspicious_modules:
            files.replace_string(self.modules_konfig_path, "blacklist " + module, "")

        return action.ActionResult()


class FixSyslogLogrotateConfig(action.ActiveAction):
    config_path: str
    path_to_backup: str
    right_logrotate_config: str

    def __init__(self, store_dir: str):
        self.name = "fix logrotate config for rsyslog"
        self.config_path = "/etc/logrotate.d/syslog"
        self.path_to_backup = store_dir + "/syslog.logrotate.bak"
        self.right_logrotate_config = """
/var/log/cron
/var/log/messages
/var/log/secure
/var/log/spooler
{
    missingok
    sharedscripts
    postrotate
        /usr/bin/systemctl kill -s HUP rsyslog.service >/dev/null 2>&1 || true
    endscript
}
"""

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        shutil.move(self.config_path, self.path_to_backup)

        with open(self.config_path, "w") as f:
            f.write(self.right_logrotate_config)

        # File installed from the package not relay on our goals because
        # it will rotate /var/log/maillog, which should be processed from plesk side
        rpmnew_file = self.config_path + ".rpmnew"
        if os.path.exists(rpmnew_file):
            os.remove(rpmnew_file)

        motd.add_finish_ssh_login_message(f"The logrotate configuration for rsyslog has been updated. The old configuration has been saved as {self.path_to_backup}\n")
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class RecreateAwstatConfigurationFiles(action.ActiveAction):
    def __init__(self):
        self.name = "recreate awstat configuration files for domains"

    def _is_required(self) -> bool:
        return os.path.exists("/etc/awstats/awstats.model.conf")

    def get_awstat_domains(self) -> typing.Set[str]:
        domains_awstats_directory = "/usr/local/psa/etc/awstats/"
        domains = set()
        for awstat_config_file in os.listdir(domains_awstats_directory):
            if awstat_config_file.startswith("awstats.") and awstat_config_file.endswith("-http.conf"):
                domains.add(awstat_config_file.split("awstats.")[-1].rsplit("-http.conf")[0])
        return domains

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        rpm.handle_all_rpmnew_files("/etc/awstats")

        for domain in self.get_awstat_domains():
            log.info(f"Recreating awstat configuration for domain: {domain}")
            util.logged_check_call(
                [
                    "/usr/sbin/plesk", "sbin", "webstatmng", "--set-configs",
                    "--stat-prog", "awstats", "--domain-name", domain
                ], stdin=subprocess.DEVNULL
            )
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self) -> int:
        # Estimate 100 ms per configuration we have to recreate
        return int(len(self.get_awstat_domains()) / 10) + 5
