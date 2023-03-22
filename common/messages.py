

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

FAIL_MESSAGE_HEAD = """
\033[91m**************************************************************************************
The conversion process has failed. There are last 100 lines of the {} file:
**************************************************************************************\033[0m
"""

FAIL_MESSAGE_TAIL = """
\033[91m**************************************************************************************
The conversion process has failed. See the {} file for more information.
Last 100 lines of the file are shown above.
For assistance, call 'centos2alma --prepare-feedback' and follow instructions.
**************************************************************************************\033[0m
"""

TIME_EXCEEDED_MESSAGE = """
\033[91m**************************************************************************************
The conversion process is taking too long. It may be stuck.
See the /var/log/plesk/centos2alma.log file for more information.
It is safe to interrupt the process with Ctrl+C and restart it from the same stage.
**************************************************************************************\033[0m
"""

FEEDBACK_IS_READY_MESSAGE = """
\033[92m**************************************************************************************
Feedback archive is ready. You can find it here: {feedback_archive_path}
For further investigation create an issue in the GitHub repository - https://github.com/plesk/distupgrader/issues.
Attach the feedback archive to the issue and describe the problem.
**************************************************************************************\033[0m
"""
