

CONVERT_RESTART_MESSAGE = """
\033[92m**************************************************************************************
The preparation process is over. The system will be rebooted now to perform the conversion inside a temporary upgrade distro.
You cannot connect to the instance via ssh during this process. To monitor the process, you could use a console port.
The conversion process will takes about 30 minutes. Current server time: {}.
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
Please contact us on github.com/plesk/distupgrader/issues or our support team with this log file attached.
**************************************************************************************\033[0m
"""

TIME_EXCEEDED_MESSAGE = """
\033[91m**************************************************************************************
The conversion process time is exceeded. This may mean that the process is stuck.
Please check the log file \033[93m{}\033[91m for more details.
You could use Ctrl+C to interrupt the process and call it again.
**************************************************************************************\033[0m
"""
