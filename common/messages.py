# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.

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
The conversion process has failed. Here are the last 100 lines of the {} file:
**************************************************************************************\033[0m
"""

FAIL_MESSAGE_TAIL = """
\033[91m**************************************************************************************
The conversion process has failed. See the {} file for more information.
The last 100 lines of the file are shown above.
For assistance, call 'centos2alma --prepare-feedback' and follow the instructions.
**************************************************************************************\033[0m
"""

TIME_EXCEEDED_MESSAGE = """
\033[91m**************************************************************************************
The conversion process is taking too long. It may be stuck. Please verify if the process is
still running by checking if logfile /var/log/plesk/centos2alma.log continues to update.
It is safe to interrupt the process with Ctrl+C and restart it from the same stage.
**************************************************************************************\033[0m
"""

FEEDBACK_IS_READY_MESSAGE = """
\033[92m**************************************************************************************
The feedback archive is ready. You can find it here: {feedback_archive_path}
For further assistance, create an issue in our GitHub repository - https://github.com/plesk/centos2alma/issues.
Please attach the feedback archive to the created issue and provide as much information about the problem as you can.
**************************************************************************************\033[0m
"""

REBOOT_WARN_MESSAGE = """\r\033[93m****************************** WARNING ***********************************************
\033[92mThe conversion is ready to begin. The server will be rebooted in {delay} seconds.
The conversion process will take approximately 25 minutes. If you wish to prevent the reboot, simply
terminate the centos2alma process. Please note that Plesk functionality is currently unavailable.
\033[93m**************************************************************************************\033[0m
"""
