# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from common import action, motd, rpm, util

import os

SPAMASSASIN_CONFIG_PATH = "/etc/mail/spamassassin/init.pre"


class FixSpamassassinConfig(action.ActiveAction):
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


class CheckSpamassassinPlugins(action.CheckAction):
    def __init__(self):
        self.name = "check spamassassin additional plugins enabled"
        self.description = """There are additional plugins enabled in spamassassin configuration:
\t- {}

They will not be available after the conversion. Please disable them manually or use --disable-spamassasin-plugins option to force script to remove them automatically.
"""
        self.supported_plugins = [
            "Mail::SpamAssassin::Plugin::URIDNSBL",
            "Mail::SpamAssassin::Plugin::Hashcash",
            "Mail::SpamAssassin::Plugin::SPF",
        ]

    def _do_check(self) -> bool:
        if not os.path.exists(SPAMASSASIN_CONFIG_PATH):
            return True

        unsupported_plugins = []
        with open(SPAMASSASIN_CONFIG_PATH, "r") as fp:
            for loadline in [line for line in fp.readlines() if line.startswith("loadplugin")]:
                plugin = loadline.rstrip().split(' ')[1]
                if plugin not in self.supported_plugins:
                    unsupported_plugins.append(plugin)

        if not unsupported_plugins:
            return True

        self.description = self.description.format("\n\t- ".join(unsupported_plugins))
        return False
