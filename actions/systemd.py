# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import os

from common import action, systemd, util


class RulePleskRelatedServices(action.ActiveAction):

    def __init__(self):
        self.name = "rule plesk services"
        plesk_known_systemd_services = [
            "crond.service",
            "dovecot.service",
            "drwebd.service",
            "fail2ban.service",
            "httpd.service",
            "mailman.service",
            "mariadb.service",
            "mysqld.service",
            "named-chroot.service",
            "plesk-ext-monitoring-hcd.service",
            "plesk-ssh-terminal.service",
            "plesk-task-manager.service",
            "plesk-web-socket.service",
            "psa.service",
            "sw-collectd.service",
            "sw-cp-server.service",
            "sw-engine.service",
        ]
        self.plesk_systemd_services = [service for service in plesk_known_systemd_services if systemd.is_service_exists(service)]

        # Oneshot services are special, so they shouldn't be started on revert or after conversion, just enabled
        self.oneshot_services = [
            "plesk-ip-remapping.service",
        ]

        # We don't remove postfix service when remove it during qmail installation
        # so we should choose the right smtp service, otherwise they will conflict
        if systemd.is_service_exists("qmail.service"):
            self.plesk_systemd_services.append("qmail.service")
        elif systemd.is_service_exists("postfix.service"):
            self.plesk_systemd_services.append("postfix.service")

    def _prepare_action(self):
        util.logged_check_call(["/usr/bin/systemctl", "stop"] + self.plesk_systemd_services)
        util.logged_check_call(["/usr/bin/systemctl", "disable"] + self.plesk_systemd_services + self.oneshot_services)

    def _post_action(self):
        util.logged_check_call(["/usr/bin/systemctl", "enable"] + self.plesk_systemd_services + self.oneshot_services)
        # Don't do startup because the services will be started up after reboot at the end of the script anyway.

    def _revert_action(self):
        util.logged_check_call(["/usr/bin/systemctl", "enable"] + self.plesk_systemd_services + self.oneshot_services)
        util.logged_check_call(["/usr/bin/systemctl", "start"] + self.plesk_systemd_services)

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        return 5

    def estimate_revert_time(self):
        return 10


class AddUpgradeSystemdService(action.ActiveAction):

    def __init__(self, script_path, options):
        self.name = "adding centos2alma resume service"

        self.script_path = script_path
        # ToDo. It's pretty simple to forget to add argument here, so maybe we should find another way
        self.options = [
            (" --upgrade-postgres", options.upgrade_postgres_allowed),
            (" --verbose", options.verbose),
            (" --no-reboot", options.no_reboot),
        ]

        self.service_name = 'plesk-centos2alma.service'
        self.service_file_path = os.path.join('/etc/systemd/system', self.service_name)
        self.service_content = '''
[Unit]
Description=First boot service for upgrade process from CentOS 7 to AlmaLinux8.
After=network.target network-online.target

[Service]
Type=simple
# want to run it once per boot time
RemainAfterExit=yes
ExecStart={script_path} -s finish {arguments}

[Install]
WantedBy=multi-user.target
'''

    def _prepare_action(self):
        arguments = ""
        for argument, enabled in self.options:
            if enabled:
                arguments += argument

        with open(self.service_file_path, "w") as dst:
            dst.write(self.service_content.format(script_path=self.script_path, arguments=arguments))

        util.logged_check_call(["/usr/bin/systemctl", "enable", self.service_name])

    def _post_action(self):
        if os.path.exists(self.service_file_path):
            util.logged_check_call(["/usr/bin/systemctl", "disable", self.service_name])

            os.remove(self.service_file_path)

    def _revert_action(self):
        if os.path.exists(self.service_file_path):
            util.logged_check_call(["/usr/bin/systemctl", "disable", self.service_name])

            os.remove(self.service_file_path)


class StartPleskBasicServices(action.ActiveAction):

    def __init__(self):
        self.name = "starting plesk services"
        self.plesk_basic_services = [
            "mariadb.service",
            "mysqld.service",
            "plesk-task-manager.service",
            "plesk-web-socket.service",
            "sw-cp-server.service",
            "sw-engine.service",
        ]
        self.plesk_basic_services = [service for service in self.plesk_basic_services if systemd.is_service_exists(service)]

    def _enable_services(self):
        # MariaDB could be started before, so we should stop it first
        util.logged_check_call(["/usr/bin/systemctl", "stop", "mariadb.service"])

        util.logged_check_call(["/usr/bin/systemctl", "enable"] + self.plesk_basic_services)
        util.logged_check_call(["/usr/bin/systemctl", "start"] + self.plesk_basic_services)

    def _prepare_action(self):
        pass

    def _post_action(self):
        self._enable_services()

    def _revert_action(self):
        self._enable_services()