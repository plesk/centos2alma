# Сonvert a CentOS 7 server with Plesk to AlmaLinux 8

CentOS 7 to AlmaLinux 8 conversion tool
## Introduction
This script is the official tool for converting a CentOS 7 server with Plesk to AlmaLinux 8. It uses the [AlmaLinux ELevate tool](https://wiki.almalinux.org/elevate/ELevate-quickstart-guide.html), which is based on the [leapp modernization framework](https://leapp.readthedocs.io/en/latest/). The script includes additional repository and configuration support provided by Plesk.

## Preparation
To avoid downtime and data loss, make sure you have read and understood the following information before using the script:
1. Back up all your databases and have the means to restore them. The script uses standard MariaDB and PostgreSQL tools to upgrade the databases, but this does not guarantee that the process will be free of issues.
2. Ensure that you have a way to restart the server without a direct SSH connection. The conversion process may get stuck once the server boots into the temporary OS distribution that does not start any network interfaces. You can use a serial port connection to the server to monitor the status of the conversion process in real time, and to reboot the server if necessary.
3. We strongly recommend that you create a snapshot you can use as a recovery point in case the conversion process fails.
4. Read the [Known problems](#known-problems) section below for the list of known issues.

## Timing
The conversion process should run between 30 and 60 minutes. **Plesk services, hosted websites, and emails will be unavailable during the entirety of the conversion process**. The conversion process itself consists of three stages:
- Preparation, which takes between 15 and 25 minutes.
- Conversion, which takes between 15 and 30 minutes. During this stage, the server will not be available remotely. You can monitor the progress via a serial port console.
- Finalization, which takes between 5 and 10 minutes.

## Known issues
### Blockers
Do not use the script if any of the following is true:
- **You are running an OS other than CentOS 7.9**. The script was not tested on other Red Hat Enterprise Linux 7-based distributions. The conversion process may have unexpected results if started on a server not running CentOS 7.9. So we add checks to avoid any actions on such kinds of servers.
- **Plesk version is 18.0.42 or earier**. The script only supports Plesk 18.0.43 and later.
- **PHP 7.1 and earlier are not supported** in AlmaLinux 8, and will not receive any updates after the conversion. These PHP versions are deprecated and may have security vulnerabilities. So we force to remove this versions before the conversion.

## Requirements
- Plesk 18.0.43 or later.
- CentOS 7.9 or later. 
- At least 5 GB of free disk space.
- At least 1 GB of RAM.

## Using the script
To retrieve the latest available version of the tool, please navigate to the "Releases" section. Once there, locate the most recent version of the tool and download the zip archive. The zip archive will contain the centos2alma tool binary.

To prepare the latest version of the tool for use from a command line, please run the following commands:
```shell
> wget https://github.com/plesk/centos2alma/releases/download/1.0.0/distupgrader_1_0_0.zip
> unzip distupgrader_1_0_0.zip
> chmod 755 centos2alma
```

To monitor the conversion process, we recommend using the ['screen' utility](https://www.gnu.org/software/screen/) to run the script in the background. To do so, run the following command:
```shell
> screen -S centos2alma
> ./centos2alma
```
If you lose your SSH connection to the server, you can reconnect to the screen session by running the following command:
```shell
> screen -r centos2alma
```


You can also call centos2alma in the background:
```shell
> ./centos2alma &
```
And monitor its status with the '--status' or '--monitor' flags:
```shell
> ./centos2alma --status
> ./centos2alma --monitor
... live monitor session ...
```


This will start the conversion process. During the process, Plesk services will stop, and hosted websites will not be accessible. At the end of the preparation stage, the server will reboot.
Next, a temporary OS distribution will be used to convert your CentOS 7 system to AlmaLinux 8. This process will take approximately 20 minutes. Once completed, the server will reboot once more. The centos2alma script will then perform the final stages of reconfiguring and restoring Plesk-related services, configurations, and databases. This will take some time, depending on the number of hosted websites.
Once the process is complete, the centos2alma script will reboot the server one last time. After that, Plesk should return to normal operation.
On the next SSH login, you will be greeted with the following message:
```
===============================================================================
Message from Plesk centos2alma tool:
The server has been converted to AlmaLinux 8.
You can remove this message from the /etc/motd file.
===============================================================================
```

### Conversion stage options
The conversion process consists of three stage options: "start", and "finish". To run stages individually, use the "--start", and "--finish" flags, or the "-s" flag with name of the stage you want to run.
1. The "start" stage installs and configures ELevate, disables Plesk services and runs ELevate. It then stops Plesk services and reboots the server.
2. The "finish" stage must be called on the first boot of AlmaLinux 8. You can rerun this stage if something goes wrong during the first boot to ensure that the problem is fixed and Plesk is ready to use.

### Other arguments

### Logs
If something goes wrong, read the logs to identify the problem. You can also read the logs to check the status of the finish stage during the first boot.
The centos2alma writes its log to the '/var/log/plesk/centos2alma.log' file, as well as to stdout.
The ELevate writes its log to the '/var/log/leapp/leapp-upgrade.log' file. Reports can be found in the '/var/log/leapp/leapp-report.txt' and the '/var/log/leapp/leapp-report.json' files.

### Revert
If the script fails during the the "start" stage before the reboot, you can use the centos2alma script with the '-r' or '--revert' flags to restore Plesk to normal operation. The centos2alma will undo some of the changes it made and restart Plesk services. Once you have resolved the root cause of the failure, you can attempt the conversion again.
Note:
- You cannot use revert to undo the changes after the first reboot triggered by centos2alma.
- Revert does not remove Leapp or packages installed by Leapp. Neither does it free persistent storage disk space reserved by Leapp.

### Check the status of the conversion process and monitor its progress
To check the status of the conversion process, use the '--status' flag. You can see the current stage of the conversion process, the elapsed time, and the estimated time until finish.
```shell
> ./centos2alma --status
``` 

To monitor the progress of the conversion process in real time, The conversion process can be monitored in real time using the '--monitor' flag.
```shell
> ./centos2alma --monitor
( stage 3 / action re-installing plesk components  ) 02:26 / 06:18
```

## Issue handling
### Leapp unable to handle packages
Leapp may not be able to handle certain installed packages, especially those installed from custom repositories. In this case, the centos2alma will fail while running leapp preupgrade or leapp upgrade. The easiest way to fix this issue is to remove the package(s), and then reinstall them once the conversion is complete.
### Temporary OS distribution hangs
This issue may occur, for example, if there is a custom python installation on the server. The conversion process will fail while upgrading the temporary OS distribution, and the temporary OS will hang with no notification. To identify the issue, connect to the server using a serial port console and check the status of the conversion process. To fix the issue, reboot the server. Note that an unfinished installation process may result in missing packages and other issues.

### centos2alma finish fails on the first boot
If something goes wrong during the finish stage, you will be informed on the next SSH login with this message:
```
===============================================================================
Message from Plesk centos2alma tool:
Something went wrong during the final stage of CentOS 7 to AlmaLinux 8 conversion
See the /var/log/plesk/centos2alma.log file for more information.
You can remove this message from the /etc/motd file.
===============================================================================
```
You can read the centos2alma log to troubleshoot the issue. If the centos2alma finish stage fails for any reason, once you have resolved the root cause of the failure, you can retry by running 'centos2alma -s finish'.
### Send feedback
If you got any error, please [create an issue on github](https://github.com/plesk/centos2alma/issues). To do generate feedback archive by calling the tool with '-f' or '--prepare-feedback' flags.
```shell
./centos2alma --prepare-feedback
```
Describe your problem and attach the feedback archive to the issue.