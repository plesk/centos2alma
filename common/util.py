import subprocess

import common


def logged_check_call(cmd, **kwargs):
    # ToDo. The solution looks not really thread safety.
    # It's fine until we decide to run actions in parallel.
    common.log.info("Running: {cmd!s}. Output:".format(cmd=cmd))
    with open(common.DEFAULT_LOG_FILE, "a") as log:
        kwargs["stdout"] = log
        kwargs["stderr"] = log
        subprocess.check_call(cmd, **kwargs)
