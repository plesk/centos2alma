from .action import ActiveAction

import subprocess
import os


class RulePleskRelatedServices(ActiveAction):

    def __init__(self):
        self.name = "rule plesk services"
        plesk_known_systemd_services = [
            "crond.service",
            "dovecot.service",
            "fail2ban.service",
            "httpd.service",
            "mailman.service",
            "mariadb.service",
            "named-chroot.service",
            "plesk-ext-monitoring-hcd.service",
            "plesk-ip-remapping.service",
            "plesk-ssh-terminal.service",
            "plesk-task-manager.service",
            "plesk-web-socket.service",
            "postfix.service",
            "psa.service",
            "spamassassin.service",
            "sw-collectd.service",
            "sw-cp-server.service",
            "sw-engine.service",
        ]
        self.plesk_systemd_services = [service for service in plesk_known_systemd_services if self._is_service_exsists(service)]

    def _is_service_exsists(self, service):
        return os.path.exists(os.path.join("/usr/lib/systemd/system/", service))

    def _prepare_action(self):
        subprocess.check_call(["systemctl", "stop"] + self.plesk_systemd_services)
        subprocess.check_call(["systemctl", "disable"] + self.plesk_systemd_services)

    def _post_action(self):
        subprocess.check_call(["systemctl", "enable"] + self.plesk_systemd_services)
        # Don't do startup because the services will be started up after reboot at the end of the script anyway.


class AddUpgradeSystemdService(ActiveAction):

    def __init__(self, script_path):
        self.name = "adding distupgrader resume service"
        self.script_path = script_path
        self.service_name = 'plesk-distugrader.service'
        self.service_file_path = os.path.join('/etc/systemd/system', self.service_name)
        self.service_content = '''
[Unit]
Description=First boot service for upgrade process from CentOS 7 to AlmaLinux8.
After=network.target network-online.target

[Service]
Type=simple
# want to run it once per boot time
RemainAfterExit=yes
ExecStart={script_path} -s finish

[Install]
WantedBy=multi-user.target
'''

    def _prepare_action(self):
        with open(self.service_file_path, "w") as dst:
            dst.write(self.service_content.format(script_path=self.script_path))

        subprocess.check_call(["systemctl", "enable", self.service_name])

    def _post_action(self):
        subprocess.check_call(["systemctl", "disable", self.service_name])

        if os.path.exists(self.service_file_path):
            os.remove(self.service_file_path)


class StartPleskBasicServices(ActiveAction):

    def __init__(self):
        self.name = "starting plesk services"
        self.plesk_basic_services = [
            "mariadb.service",
            "plesk-task-manager.service",
            "plesk-web-socket.service",
            "sw-cp-server.service",
            "sw-engine.service",
        ]

    def _prepare_action(self):
        pass

    def _post_action(self):
        subprocess.check_call(["systemctl", "enable"] + self.plesk_basic_services)
        subprocess.check_call(["systemctl", "start"] + self.plesk_basic_services)