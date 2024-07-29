# Copyright 1999 - 2024. Plesk International GmbH. All rights reserved.
from pleskdistup.common import action, util

import os


class DoCentos2AlmaConvert(action.ActiveAction):
    leapp_ovl_size: int

    def __init__(self, leapp_ovl_size: int = 4096):
        self.name = "doing the conversion"
        self.leapp_ovl_size = leapp_ovl_size

    def _prepare_action(self) -> action.ActionResult:
        env_vars = os.environ.copy()
        env_vars["LEAPP_OVL_SIZE"] = str(self.leapp_ovl_size)

        util.logged_check_call(["/usr/bin/leapp", "preupgrade"], env=env_vars)
        util.logged_check_call(["/usr/bin/leapp", "upgrade"], env=env_vars)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 17 * 60
