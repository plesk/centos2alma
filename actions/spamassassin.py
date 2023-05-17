# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction

from common import motd, rpm, util

SPAMASSASIN_CONFIG_PATH = "/etc/mail/spamassassin/init.pre"


class FixSpamassassinConfig(ActiveAction):
    # Make sure the trick is preformed before any call of 'systemctl daemon-reload'
    # because we change spamassassin.service configuration in scope of this action.
    def __init__(self):
        self.name = "fix spamassassin configuration"

    def _is_required(self) -> bool:
        return rpm.is_package_installed("psa-spamassassin")

    def _prepare_action(self) -> None:
        util.logged_check_call(["/usr/bin/systemctl", "stop", "spamassassin.service"])
        util.logged_check_call(["/usr/bin/systemctl", "disable", "spamassassin.service"])

    def _post_action(self) -> None:
        util.logged_check_call(["/usr/sbin/plesk", "sbin", "spammng", "--enable"])
        util.logged_check_call(["/usr/sbin/plesk", "sbin", "spammng", "--update", "--enable-server-configs", "--enable-user-configs"])

        util.logged_check_call(["/usr/bin/systemctl", "daemon-reload"])
        util.logged_check_call(["/usr/bin/systemctl", "enable", "spamassassin.service"])

        if rpm.handle_rpmnew(SPAMASSASIN_CONFIG_PATH):
            motd.add_finish_ssh_login_message("Note that spamassasin configuration '{}' was changed during conversion. "
                                              "Original configuration can be found in {}.rpmsave.".format(SPAMASSASIN_CONFIG_PATH, SPAMASSASIN_CONFIG_PATH))

    def _revert_action(self) -> None:
        util.logged_check_call(["/usr/bin/systemctl", "enable", "spamassassin.service"])
        util.logged_check_call(["/usr/bin/systemctl", "start", "spamassassin.service"])
