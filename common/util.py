import subprocess

import common


def logged_check_call(cmd, **kwargs):
    common.log.info("Running: {cmd!s}. Output:".format(cmd=cmd))

    # I beleive we should be able pass argument to the subprocess function
    # from the caller. So we have to inject stdout/stderr/universal_newlines
    kwargs["stdout"] = subprocess.PIPE
    kwargs["stderr"] = subprocess.STDOUT
    kwargs["universal_newlines"] = True

    process = subprocess.Popen(cmd, **kwargs)
    while None is process.poll():
        line = process.stdout.readline()
        if line and line.strip():
            common.log.info(line.strip(), to_stream=False)

    if process.returncode != 0:
        common.log.err(f"Command '{cmd}' failed with return code {process.returncode}")
        raise subprocess.CalledProcessError(process.returncode, cmd)

    common.log.info("Command '{cmd}' finished successfully".format(cmd=cmd))

