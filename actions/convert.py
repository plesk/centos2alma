from .action import ActiveAction

import subprocess


class DoConvert(ActiveAction):
    def __init__(self):
        self.name = "making the conversation"

    def _prepare_action(self):
        subprocess.check_call(["leapp", "preupgrade"])
        subprocess.check_call(["leapp", "upgrade"])

    def _post_action(self):
        pass

    def _revert_action(self):
        pass
