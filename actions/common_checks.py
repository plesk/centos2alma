# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import CheckAction

import collections
import os
import platform
import shutil
import subprocess

from common import files, log, plesk, rpm


class PleskInstallerNotInProgress(CheckAction):
    def __init__(self):
        self.name = "checking if Plesk installer is in progress"
        self.description = """The conversion process cannot continue because Plesk Installer is working.
\tPlease wait until it finishes or call 'plesk installer stop' to abort it.
"""

    def _do_check(self):
        installer_status = subprocess.check_output(["/usr/sbin/plesk", "installer", "--query-status", "--enable-xml-output"],
                                                   universal_newlines=True)
        if "query_ok" in installer_status:
            return True
        return False


class DistroIsCentos79(CheckAction):
    def __init__(self):
        self.name = "checking if distro is CentOS7"
        self.description = """You are running a distributive other than CentOS 7.9. At the moment, only CentOS 7.9 is supported.
\tIf you are running an earlier Centos 7 release, update to Centos 7.9 and try again.
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
        self.description = "You are running a distributive other than AlmaLinux 8. The finalization stage can only be started on AlmaLinux 8."

    def _do_check(self):
        distro = platform.linux_distribution()
        major_version = distro[1].split(".")[0]
        if distro[0] == "AlmaLinux" and int(major_version) == 8:
            return True
        return False


class PleskVersionIsActual(CheckAction):
    def __init__(self):
        self.name = "checking if Plesk version is actual"
        self.description = "Only Plesk Obsidian 18.0.43 or later is supported. Update Plesk to version 18.0.43 or later and try again."

    def _do_check(self):
        try:
            major, _, iter, _ = plesk.get_plesk_version()
            return int(major) >= 18 and int(iter) >= 43
        except Exception as ex:
            log.warn("Checking plesk version is failed with error: {}".format(ex))

        return False


class CheckAvailableSpace(CheckAction):
    def __init__(self):
        self.name = "checking available space"
        self.required_space = 5 * 1024 * 1024 * 1024  # 5GB
        self.description = """There is insufficient disk space available. Leapp requires a minimum of {} of free space
\ton the disk where the '/var/lib' directory is located. Available space: {}. 
\tFree up enough disk space and try again.
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
        self.description = """Outdated PHP versions were detected: '{}'. To proceed with the conversion:
\t1.  Switch the following domains to PHP 7.2 or later:
\t- {}

\tYou can do so by running the following command:
\t> plesk bin domain -u [domain] -php_handler_id plesk-php80-fastcgi

\t2. Remove outdated PHP packages via Plesk Installer.
"""

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

        php_hanlers = {"'{}-fastcgi'", "'{}-fpm'", "'{}-fpm-dedicated'"}
        outdated_php_handlers = []
        for installed in installed_pkgs:
            outdated_php_handlers += [handler.format(installed) for handler in php_hanlers]

        try:
            looking_for_domains_sql_request = """
                SELECT d.name FROM domains d JOIN hosting h ON d.id = h.dom_id WHERE h.php_handler_id in ({});
            """.format(", ".join(outdated_php_handlers))
            outdated_php_domains = subprocess.check_output(["/usr/sbin/plesk", "db", looking_for_domains_sql_request],
                                                           universal_newlines=True)
            outdated_php_domains = [domain[2:-2] for domain in outdated_php_domains.splitlines()
                                    if domain.startswith("|") and not domain.startswith("| name ")]
            outdated_php_domains = "\n\t- ".join(outdated_php_domains)
        except Exception:
            outdated_php_domains = "Unable to get domains list. Please check it manually."

        self.description = self.description.format(", ".join([outdated_php_packages[installed] for installed in installed_pkgs]),
                                                   outdated_php_domains)
        return False


class CheckGrubInstalled(CheckAction):
    def __init__(self):
        self.name = "checking if grub is installed"
        self.description = """The /etc/default/grub file is missing. GRUB may not be installed.
\tMake sure that GRUB is installed and try again.
"""

    def _do_check(self):
        return os.path.exists("/etc/default/grub")


class CheckNoMoreThenOneKernelNamedNIC(CheckAction):
    def __init__(self):
        self.name = "checking if there is more than one NIC interface using ketnel-name"
        self.description = """The system has one or more network interface cards (NICs) using kernel-names (ethX).
\tLeapp cannot guarantee the interface names' stability during the conversion.
\tGive those NICs persistent names (enpXsY) to proceed with the conversion.
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
        self.description = "The system is running in a container-like environment ({}). The conversion is not supported for such systems."

    def _is_docker(self):
        return os.path.exists("/.dockerenv")

    def _is_podman(self):
        return os.path.exists("/run/.containerenv")

    def _is_vz_like(self):
        return os.path.exists("/proc/vz")

    def _do_check(self):
        if self._is_docker():
            self.description = self.description.format("Docker container")
            return False
        elif self._is_podman():
            self.description = self.description.format("Podman container")
            return False
        elif self._is_vz_like():
            self.description = self.description.format("Virtuozzo container")
            return False

        return True


class CheckLastInstalledKernelInUse(CheckAction):
    def __init__(self):
        self.name = "checking if the last installed kernel is in use"
        self.description = """The last installed kernel is not in use.
\tThe kernel version in use is '{}'. The last installed kernel version is '{}'.
\tReboot the system to use the last installed kernel.
"""

    def _get_kernel_vesion__in_use(self):
        return subprocess.check_output(["/usr/bin/uname", "-r"], universal_newlines=True).strip()

    def _get_last_installed_kernel_version(self):
        versions = subprocess.check_output(["/usr/bin/rpm", "-q", "-a", "kernel"], universal_newlines=True).splitlines()
        return max(versions).split("-", 1)[-1]

    def _is_realtime_installed(self):
        return len(subprocess.check_output(["/usr/bin/rpm", "-q", "-a", "kernel-rt"], universal_newlines=True).splitlines()) > 0

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


class CheckIsLocalRepositoryNotPresent(CheckAction):
    def __init__(self):
        self.name = "checking if the local repository is present"
        self.description = """There are rpm repository with local storage present. Leapp is not support such kind of repositories.
\tPlease remove the local repositories to proceed the conversion. Files where locally stored repositories are defined:
\t- {}
"""

    def _is_repo_contains_local_storage(self, repo_file):
        with open(repo_file) as f:
            repository_content = f.read()
            return ("baseurl=file:" in repository_content or "baseurl = file:" in repository_content or
                    "metalink=file:" in repository_content or "metalink = file:" in repository_content or
                    "mirrorlist=file:" in repository_content or "mirrorlist = file:" in repository_content)

    def _do_check(self):
        # CentOS-Media.repo is a special file which is created by default on CentOS 7. It contains a local repository
        # but leapp allows it anyway. So we could skip it.
        local_repositories_files = [file for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["*.repo"])
                                    if os.path.basename(file) != "CentOS-Media.repo" and self._is_repo_contains_local_storage(file)]

        if len(local_repositories_files) == 0:
            return True

        self.description = self.description.format("\n\t- ".join(local_repositories_files))
        return False


class CheckRepositoryDuplicates(CheckAction):
    def __init__(self):
        self.name = "checking if there are duplicate repositories"
        self.description = """There are duplicate repositories present:
\t- {}

\tPlease remove the duplicate to proceed the conversion.
"""

    def _do_check(self):
        repositories = []
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["*.repo"])
        for repofile in repofiles:            
            with open(repofile, "r") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line.startswith("[") and line.endswith("]"):
                        repositories.append(line)

        duplicates = [repository for repository, count in collections.Counter(repositories).items() if count > 1]
        if len(duplicates) == 0:
            return True

        self.description = self.description.format("\n\t- ".join(duplicates))
        return False


class CheckPackagesUpToDate(CheckAction):
    def __init__(self):
        self.name = "checking if all packages are up to date"
        self.description = "There are packages which are not up to date. Call `yum update -y && reboot` to update the packages.\n"

    def _do_check(self):
        subprocess.check_call(["/usr/bin/yum", "clean", "all"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        checker = subprocess.run(["/usr/bin/yum", "check-update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return checker.returncode == 0
