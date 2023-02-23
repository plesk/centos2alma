

CONVERT_RESTART_MESSAGE = """
\033[92m**************************************************************************************
The preparation process is over. The system will be rebooted now to perform the conversion inside a temporary upgrade distro.
You cannot connect to the instance via ssh during this process. To monitor the process, you could use a console port.
The conversion process will takes about 25 minutes. Current server time: {}.
When you able to connect to the instance again, you could use the following command to check the conversion status:
    distupgrader --status
or
    distupgrader --monitor
**************************************************************************************\033[0m
"""

FINISH_RESTART_MESSAGE = """
\033[92m**************************************************************************************
The conversion process is over. The system will be rebooted now to complete the conversion.
**************************************************************************************\033[0m
"""

REVET_FINISHED_MESSAGE = """
\033[92m**************************************************************************************
The revert process is over. Now your plesk should be in working state.
**************************************************************************************\033[0m
"""

FAIL_MESSAGE = """
\033[91m**************************************************************************************
The conversion process has been failed. Please check the log file \033[93m{}\033[91m for more details.
Please submit an issue to https://github.com/plesk/distupgrader/issues with attached log file.
**************************************************************************************\033[0m
"""

TIME_EXCEEDED_MESSAGE = """
\033[91m**************************************************************************************
The conversion process time is exceeded. This may mean that the process is stuck.
Please check the log file \033[93m{}\033[91m for more details.
You could use Ctrl+C to interrupt the process and call it again.
**************************************************************************************\033[0m
"""
