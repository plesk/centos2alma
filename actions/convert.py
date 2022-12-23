from .action import ActivaAction

import subprocess


class DoConvert(ActivaAction):
    def __init__(self):
        self.name = "do converation with leapp"

    def _prepare_action(self):
        subprocess.check_call(["leapp", "preupgrade"])
        subprocess.check_call(["leapp", "upgrade"])

    def _post_action(self):
        pass
