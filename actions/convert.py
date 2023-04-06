# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction

from common import util


class DoConvert(ActiveAction):
    def __init__(self):
        self.name = "making the conversation"

    def _prepare_action(self):
        util.logged_check_call(["/usr/bin/leapp", "preupgrade"])
        util.logged_check_call(["/usr/bin/leapp", "upgrade"])

    def _post_action(self):
        pass

    def _revert_action(self):
        pass

    def estimate_prepare_time(self):
        return 17 * 60
