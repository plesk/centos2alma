# The script to convert CentOS7 to AlmaLinux 8 with installed Plesk panel

## Introduction
This script utilizes the [AlmaLinux ELevate tool](https://wiki.almalinux.org/elevate/ELevate-quickstart-guide.html), which is based on the [leapp modernization framework](https://leapp.readthedocs.io/en/latest/), to perform the conversion of a server running Plesk on CentOS 7 to AlmaLinux 8.
The script includes additional repository and configuration support provided by Plesk. This is the official method for converting a server with Plesk from CentOS 7 to AlmaLinux 8.

## Preparation
Before using this script, it is important to take the following precautions:
1. Make sure that you have backed up all of your databases and have the means to restore them. We will be using standard mariadb and postgresql tools to upgrade the databases, and it is highly recommended to have backups in case something goes wrong.
2. Ensure that you have a way to restart the server in the event that the direct ssh connection is lost. There is a risk that the conversion process may hang in a temporary update distro that does not start any network interfaces. One way to mitigate this risk is to have a serial port connection to the server, which will allow you to monitor the upgrade distro and the first boot progress, and to reboot the server if necessary.
3. It may be helpful to have a snapshot that can be used as a recovery point in case the conversion process fails.

## How to use the script

To use the script, simply run it without any arguments:
```shell
> ./distupgrader
```
This will start the conversion process. Please note that during this process, Plesk services will be temporarily shut down and hosted sites will not be accessible. At the end of the preparation process the server will be rebooted.
Next, a temporary distro will be used to convert your CentOS 7 system to AlmaLinux 8. This process is estimated to take approximately 20 minutes. Once completed, the server will undergo another reboot. The distupgrader script will then perform the final steps of reconfiguring and restoring Plesk-related services, configurations, and databases. This may take a significant amount of time if the databases contain a large amount of data.
Once the process is complete, the distupgrader script will reboot the server one final time, at which point it should be ready to use.

### Conversion stages
The conversion process can be divided into several stages: "prepare", "start", and "finish". Use the flag "-s" to run only one stage of the conversion process.
1. The "prepare" stage should always be called first. It installs ELevate and makes additional configurations for it. This stage does not disable any services, so it can be safely run at any time.
2. The "start" stage disables Plesk-related services and runs ELevate. This will result in the stopping of Plesk services and the rebooting of the server.
3. The "finish" stage should be called on the first boot of AlmaLinux 8. The distupgrader finish can be re-run if something goes wrong during the first boot to ensure that the problem is fixed and Plesk is ready to use."

### Other arguments

### Logs
In most cases, it is not necessary to check the logs. However, if something goes wrong, the logs can be used to identify the problem. The logs can also be used to check the status of the finish stage during the first boot.
The distupgrader logs can be found in '/var/log/plesk/distupgrader.log', and will also be written to stdout.
The ELevate debug logs can be found in '/var/log/leapp/leapp-upgrade.log', and reports can be found in '/var/log/leapp/leapp-report.txt' and '/var/log/leapp/leapp-report.json'.

## Possible problems

### Leapp unable to hangle package
In some cases, leapp may not be able to handle certain installed packages, especially if they were installed from uncommon repositories. In this case, the distupgrader will fail while running leapp preupgrade or leapp upgrade with an explanatory message. The simplest way to fix this problem is to remove the old package and reinstall a similar package once the conversion is complete.
### Upgrade distro is hung
This problem may occur in rare situations, such as when a custom python installation is present. In this case, the conversion process will fail in the scope of the upgrade temporary distro, and the distro will hang without any notification. To identify the problem, you should connect to your instance using a serial port and check the status. To fix the problem, reboot the server. Note that an unfinished installation process may result in missing packages and other issues.

### Distupgrader finish failed on a first boot
The problem can be identified in the distupgrader log '/var/log/plesk/distupgrader.log'. If the distupgrader finish stage fails for any reason, you can rerun it with 'distupgrader -s finish' after addressing the cause of the failure.
## Restrictions
There is a list of known restrictions that we are actively working to resolve:
- Qmail - Authentication is broken after the conversion
- Plesk premium Antivirus - prevent MariaDB startup on the first boot of AlmaLinux
- Monitoring extension - The monitoring service cannot be enabled after the conversion
- Docker extension - Leapp is unable to perform the preupgrade, so the conversion cannot be completed
- Ruby - Ruby applications not working after a conversion