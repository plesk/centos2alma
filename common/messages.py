

CONVERT_RESTART_MESSAGE = """
\033[92m**************************************************************************************
The conversion is ready to begin. The server will now be rebooted into the temporary OS distribution.
You cannot connect to the server via SSH during this process. To monitor the process, use a serial port console.
The conversion process will take about 25 minutes. Current server time: {time}.
Once you are able to connect to the server, use one of the following commands to see or monitor the conversion status:
    {script_path} --status
or
    {script_path} --monitor
**************************************************************************************\033[0m
"""

FINISH_RESTART_MESSAGE = """
\033[92m**************************************************************************************
The conversion process has finished. The server will now reboot to finalize the conversion.
**************************************************************************************\033[0m
"""

REVET_FINISHED_MESSAGE = """
\033[92m**************************************************************************************
All changes have been reverted. Plesk should now return to normal operation.
**************************************************************************************\033[0m
"""

FAIL_MESSAGE = """
\033[91m**************************************************************************************
The conversion process has failed. See the /var/log/plesk/centos2alma.log file for more information.
For assistance, submit an issue here https://github.com/plesk/distupgrader/issues and attach this log file.
**************************************************************************************\033[0m
"""

TIME_EXCEEDED_MESSAGE = """
\033[91m**************************************************************************************
The conversion process is taking too long. It may be stuck.
See the /var/log/plesk/centos2alma.log file for more information.
It is safe to interrupt the process with Ctrl+C and restart it from the same stage.
**************************************************************************************\033[0m
"""
