# Copyright 1999 - 2025. Plesk International GmbH. All rights reserved.
from pleskdistup.common import action, leapp_configs, util

import os
import subprocess
import typing


class LeappPreupgradeRisksPreventedException(Exception):
    def __init__(self, inhibitors: typing.List[str], original_exception: Exception = None):
        super().__init__("Leapp preupgrade failed due to preventing factors being found.")
        self.inhibitors = inhibitors
        self.original_exception = original_exception

    def __str__(self):
        inhibitors_str = "\n".join(self.inhibitors)

        original_exception_str = ""
        if self.original_exception:
            original_exception_str = f"Original exception: {self.original_exception}.\n"

        return f"{super().__str__()}\n{original_exception_str}The preventing factors are:\n{inhibitors_str}"


class DoCentos2AlmaConvert(action.ActiveAction):
    leapp_ovl_size: int

    def __init__(self, leapp_ovl_size: int = 4096):
        self.name = "doing the conversion"
        self.leapp_ovl_size = leapp_ovl_size

    def _prepare_action(self) -> action.ActionResult:
        env_vars = os.environ.copy()
        env_vars["LEAPP_OVL_SIZE"] = str(self.leapp_ovl_size)

        try:
            util.log_outputs_check_call(["/usr/bin/leapp", "preupgrade"], collect_return_stdout=False, env=env_vars)
        except subprocess.CalledProcessError as e:
            inhibitors = leapp_configs.extract_leapp_report_inhibitors()
            if inhibitors:
                raise LeappPreupgradeRisksPreventedException(inhibitors, e)
            else:
                raise e

        util.log_outputs_check_call(["/usr/bin/leapp", "upgrade"], collect_return_stdout=False, env=env_vars)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 25 * 60
