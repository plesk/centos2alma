# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import CheckAction

import os
import platform
import shutil
import subprocess

from common import rpm


class PleskInstallerNotInProgress(CheckAction):
    def __init__(self):
        self.name = "checking if Plesk installer is in progress"
        self.description = "Plesk installer is in progress. Please wait until it is finished. Or use 'plesk installer stop' to abort it."

    def _do_check(self):
        installer_status = subprocess.check_output(["/usr/sbin/plesk", "installer", "--query-status", "--enable-xml-output"],
                                                   universal_newlines=True)
        if "query_ok" in installer_status:
            return True
        return False


class DistroIsCentos79(CheckAction):
    def __init__(self):
        self.name = "checking if distro is CentOS7"
        self.description = """Your distributive is not CentOS 7.9. Unfortunately we are support only CentOS 7.9 for now.
\tIf you use any other version of Centos 7 please update it to Centos 7.9.
"""

    def _do_check(self):
        distro = platform.linux_distribution()
        major_version, minor_version = distro[1].split(".")[:2]
        if distro[0] == "CentOS Linux" and int(major_version) == 7 and int(minor_version) == 9:
            return True
        return False


class DistroIsAlmalinux8(CheckAction):
    def __init__(self):
        self.name = "checking if distro is AlmaLinux8"
        self.description = "Your distributive is not AlmaLinux8. Finish stage can be started only on AlmaLinux8."

    def _do_check(self):
        distro = platform.linux_distribution()
        major_version = distro[1].split(".")[0]
        if distro[0] == "AlmaLinux" and int(major_version) == 8:
            return True
        return False


class PleskVersionIsActual(CheckAction):
    def __init__(self):
        self.name = "checking if Plesk version is actual"
        self.description = "Plesk version should be 18.0.43 or later. Please update Plesk to solve the problem."

    def _do_check(self):
        version_info = subprocess.check_output(["/usr/sbin/plesk", "version"], universal_newlines=True).splitlines()
        for line in version_info:
            if line.startswith("Product version"):
                version = line.split()[-1]
                major, _, iter, _ = version.split(".")
                if int(major) >= 18 and int(iter) >= 43:
                    return True
                break

        return False


class CheckAvailableSpace(CheckAction):
    def __init__(self):
        self.name = "checking available space"
        self.required_space = 5 * 1024 * 1024 * 1024  # 5GB
        self.description = """There is insufficient disk space available. Leapp requires a minimum of {} of free space
\ton the disk where the '/var/lib' directory is located. Available space: {}. 
\tPlease free up space and try again.
"""

    def _huminize_size(self, size):
        original = size
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{original} B"

    def _do_check(self):
        # Leapp stores rhel 8 filesystem in /var/lib/leapp
        # That's why it takes so much disk space
        available_space = shutil.disk_usage("/var/lib")[2]
        if available_space >= self.required_space:
            return True

        self.description = self.description.format(self._huminize_size(self.required_space), self._huminize_size(available_space))
        return False


class CheckOutdatedPHP(CheckAction):
    def __init__(self):
        self.name = "checking outdated PHP"
        self.description = """Outdated versions of PHP was detected. To proceed the conversion, please remove
\t'{}' through Plesk installer."""

    def _do_check(self):
        outdated_php_packages = {
            "plesk-php52": "PHP 5.2",
            "plesk-php53": "PHP 5.3",
            "plesk-php54": "PHP 5.4",
            "plesk-php55": "PHP 5.5",
            "plesk-php56": "PHP 5.6",
            "plesk-php70": "PHP 7.0",
            "plesk-php71": "PHP 7.1",
        }

        installed_pkgs = rpm.filter_installed_packages(outdated_php_packages.keys())
        if len(installed_pkgs) == 0:
            return True

        self.description = self.description.format(", ".join([outdated_php_packages[installed] for installed in installed_pkgs]))
        return False


class CheckGrubInstalled(CheckAction):
    def __init__(self):
        self.name = "checking if grub is installed"
        self.description = """It seems like grub is not installed because the /etc/default/grub file is missing.
\tPlease install it to proceed the conversion.
"""

    def _do_check(self):
        return os.path.exists("/etc/default/grub")


class CheckNoMoreThenOneKernelNamedNIC(CheckAction):
    def __init__(self):
        self.name = "checking if there is more than one NIC interface using ketnel-name"
        self.description = """The system has more then one network interface cards (NICs) using kernel-names (ethX).
\tleapp unable to guarantee interfaces names stability during the conversion.
\tPlease rename all NICs to use persistent names (enpXsY) to proceed the conversion.
\tIntarfeces: {}
"""

    def _do_check(self):
        # We can't use this method th get interfaces names, so just skip the check
        if not os.path.exists("/sys/class/net"):
            return True

        interfaces = os.listdir('/sys/class/net')
        suspicious_interfaces = [interface for interface in interfaces if interface.startswith("eth") and interface[3:].isdigit()]
        if len(suspicious_interfaces) > 1:
            self.description = self.description.format(", ".join(suspicious_interfaces))
            return False

        return True


class CheckIsInContainer(CheckAction):
    def __init__(self):
        self.name = "checking if the system not in a container"
        self.description = "The system is running in a container-like environment. The conversion is not supported for such systems."

    def _is_docker(self):
        return os.path.exists("/.dockerenv")

    def _is_podman(self):
        return os.path.exists("/run/.containerenv")

    def _is_vz_like(self):
        return os.path.exists("/proc/vz")

    def _do_check(self):
        return not (self._is_docker() or self._is_podman() or self._is_vz_like())


class CheckLastInstalledKernelInUse(CheckAction):
    def __init__(self):
        self.name = "checking if the last installed kernel is in use"
        self.description = """The last installed kernel is not in use.
\tUsed kernel version is '{}'. Last installed version is '{}'.
\tPlease reboot the system to use the last installed kernel."""

    def _get_kernel_vesion__in_use(self):
        return subprocess.check_output(["uname", "-r"], universal_newlines=True).strip()

    def _get_last_installed_kernel_version(self):
        versions = subprocess.check_output(["rpm", "-q", "-a", "kernel"], universal_newlines=True).splitlines()
        return max(versions).split("-", 1)[-1]

    def _is_realtime_installed(self):
        return len(subprocess.check_output(["rpm", "-q", "-a", "kernel-rt"], universal_newlines=True).splitlines()) > 0

    def _do_check(self):
        # For now skip checking realtime kernels. leapp will check it on it's side
        # I believe we have no much installation with realtime kernel
        if self._is_realtime_installed():
            return True

        last_installed_kernel_version = self._get_last_installed_kernel_version()
        used_kernel_version = self._get_kernel_vesion__in_use()
        if used_kernel_version != last_installed_kernel_version:
            self.description = self.description.format(used_kernel_version, last_installed_kernel_version)
            return False

        return True
