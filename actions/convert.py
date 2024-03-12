# Copyright 1999 - 2024. WebPros International GmbH. All rights reserved.
from common import action, util


class DoConvert(action.ActiveAction):
    def __init__(self):
        self.name = "doing the conversion"

    def _prepare_action(self) -> None:
        util.logged_check_call(["/usr/bin/leapp", "preupgrade"])
        util.logged_check_call(["/usr/bin/leapp", "upgrade"])

    def _post_action(self) -> None:
        pass

    def _revert_action(self) -> None:
        pass

    def estimate_prepare_time(self) -> int:
        return 17 * 60
