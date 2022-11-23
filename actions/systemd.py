from .action import Action

import subprocess


class RulePleskRelatedServices(Action):

    def __init__(self):
        self.name = "rule plesk services"
        self.plesk_systemcd_services = [
            "dovecot.service",
            "fail2ban.service",
            "httpd.service",
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

    def _prepare_action(self):
        subprocess.check_call(["systemctl", "stop"] + self.plesk_systemcd_services)
        subprocess.check_call(["systemctl", "disable"] + self.plesk_systemcd_services)

    def _post_action(self):
        subprocess.check_call(["systemctl", "enable"] + self.plesk_systemcd_services)
        subprocess.check_call(["systemctl", "start"] + self.plesk_systemcd_services)
