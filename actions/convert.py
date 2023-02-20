from .action import ActiveAction

from common import util


class DoConvert(ActiveAction):
    def __init__(self):
        self.name = "making the conversation"

    def _prepare_action(self):
        util.logged_check_call(["leapp", "preupgrade"])
        util.logged_check_call(["leapp", "upgrade"])

    def _post_action(self):
        pass

    def _revert_action(self):
        pass

    def estimate_time(self):
        return 17 * 60
