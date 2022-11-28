from .action import Action

import subprocess
import os


class RulePleskRelatedServices(Action):

    def __init__(self):
        self.name = "rule plesk services"
        plesk_known_systemcd_services = [
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
            "sw-collectd.service",
            "sw-cp-server.service",
            "sw-engine.service",
        ]
        self.plesk_systemcd_services = [service for service in plesk_known_systemcd_services if self._is_service_exsists(service)]

    def _is_service_exsists(self, service):
        return os.path.exists(os.path.join("/usr/lib/systemd/system/", service))

    def _prepare_action(self):
        subprocess.check_call(["systemctl", "stop"] + self.plesk_systemcd_services)
        subprocess.check_call(["systemctl", "disable"] + self.plesk_systemcd_services)

    def _post_action(self):
        subprocess.check_call(["systemctl", "enable"] + self.plesk_systemcd_services)
        # Don't do startup becuase the services will be started up after reboot at the end of the script anyway.
