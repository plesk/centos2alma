# Copyright 1999 - 2024. WebPros International GmbH. All rights reserved.

import collections
import os
import platform
import shutil
import subprocess

from common import action, files, log, plesk, version


class PleskInstallerNotInProgress(action.CheckAction):
    def __init__(self):
        self.name = "checking if Plesk installer is in progress"
        self.description = """The conversion process cannot continue because Plesk Installer is working.
\tPlease wait until it finishes or call 'plesk installer stop' to abort it.
"""

    def _do_check(self) -> bool:
        installer_status = subprocess.check_output(["/usr/sbin/plesk", "installer", "--query-status", "--enable-xml-output"],
                                                   universal_newlines=True)
        if "query_ok" in installer_status:
            return True
        return False


class DistroIsCentos79(action.CheckAction):
    def __init__(self):
        self.name = "checking if distro is CentOS7"
        self.description = """You are running a distributive other than CentOS 7.9. At the moment, only CentOS 7.9 is supported.
\tIf you are running an earlier Centos 7 release, update to Centos 7.9 and try again.
"""

    def _do_check(self) -> bool:
        distro = platform.linux_distribution()
        major_version, minor_version = distro[1].split(".")[:2]
        if distro[0] == "CentOS Linux" and int(major_version) == 7 and int(minor_version) == 9:
            return True
        return False


class DistroIsAlmalinux8(action.CheckAction):
    def __init__(self):
        self.name = "checking if distro is AlmaLinux8"
        self.description = "You are running a distributive other than AlmaLinux 8. The finalization stage can only be started on AlmaLinux 8."

    def _do_check(self) -> bool:
        distro = platform.linux_distribution()
        major_version = distro[1].split(".")[0]
        if distro[0] == "AlmaLinux" and int(major_version) == 8:
            return True
        return False


class PleskVersionIsActual(action.CheckAction):
    def __init__(self):
        self.name = "checking if Plesk version is actual"
        self.description = "Only Plesk Obsidian 18.0.43 or later is supported. Update Plesk to version 18.0.43 or later and try again."

    def _do_check(self) -> bool:
        try:
            major, _, iter, _ = plesk.get_plesk_version()
            return int(major) >= 18 and int(iter) >= 43
        except Exception as ex:
            log.warn("Checking plesk version is failed with error: {}".format(ex))

        return False


class CheckAvailableSpace(action.CheckAction):
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

    def _do_check(self) -> bool:
        # Leapp stores rhel 8 filesystem in /var/lib/leapp
        # That's why it takes so much disk space
        available_space = shutil.disk_usage("/var/lib")[2]
        if available_space >= self.required_space:
            return True

        self.description = self.description.format(self._huminize_size(self.required_space), self._huminize_size(available_space))
        return False


class CheckGrubInstalled(action.CheckAction):
    def __init__(self):
        self.name = "checking if grub is installed"
        self.description = """The /etc/default/grub file is missing. GRUB may not be installed.
\tMake sure that GRUB is installed and try again.
"""

    def _do_check(self) -> bool:
        return os.path.exists("/etc/default/grub")


class CheckNoMoreThenOneKernelNamedNIC(action.CheckAction):
    def __init__(self):
        self.name = "checking if there is more than one NIC interface using ketnel-name"
        self.description = """The system has one or more network interface cards (NICs) using kernel-names (ethX).
\tLeapp cannot guarantee the interface names' stability during the conversion.
\tGive those NICs persistent names (enpXsY) to proceed with the conversion.
\tIntarfeces: {}
"""

    def _do_check(self) -> bool:
        # We can't use this method th get interfaces names, so just skip the check
        if not os.path.exists("/sys/class/net"):
            return True

        interfaces = os.listdir('/sys/class/net')
        suspicious_interfaces = [interface for interface in interfaces if interface.startswith("eth") and interface[3:].isdigit()]
        if len(suspicious_interfaces) > 1:
            self.description = self.description.format(", ".join(suspicious_interfaces))
            return False

        return True


class CheckIsInContainer(action.CheckAction):
    def __init__(self):
        self.name = "checking if the system not in a container"
        self.description = "The system is running in a container-like environment ({}). The conversion is not supported for such systems."

    def _is_docker(self) -> bool:
        return os.path.exists("/.dockerenv")

    def _is_podman(self) -> bool:
        return os.path.exists("/run/.containerenv")

    def _is_vz_like(self) -> bool:
        return os.path.exists("/proc/vz")

    def _do_check(self) -> bool:
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


class CheckLastInstalledKernelInUse(action.CheckAction):
    def __init__(self):
        self.name = "checking if the last installed kernel is in use"
        self.description = """The last installed kernel is not in use.
\tThe kernel version in use is '{}'. The last installed kernel version is '{}'.
\tReboot the system to use the last installed kernel.
"""

    def _get_kernel_version_in_use(self) -> version.KernelVersion:
        curr_kernel = subprocess.check_output(["/usr/bin/uname", "-r"], universal_newlines=True).strip()
        log.debug("Current kernel version is '{}'".format(curr_kernel))
        return version.KernelVersion(curr_kernel)

    def _get_last_installed_kernel_version(self) -> version.KernelVersion:
        versions = subprocess.check_output(
            [
                "/usr/bin/rpm", "-q", "-a", "kernel", "kernel-plus", "kernel-rt-core"
            ], universal_newlines=True
        ).splitlines()

        log.debug("Installed kernel versions: {}".format(', '.join(versions)))
        versions = [version.KernelVersion(ver) for ver in versions]
        return max(versions)

    def _do_check(self) -> bool:
        last_installed_kernel_version = self._get_last_installed_kernel_version()
        used_kernel_version = self._get_kernel_version_in_use()

        if used_kernel_version != last_installed_kernel_version:
            self.description = self.description.format(str(used_kernel_version), str(last_installed_kernel_version))
            return False

        return True


class CheckIsLocalRepositoryNotPresent(action.CheckAction):
    def __init__(self):
        self.name = "checking if the local repository is present"
        self.description = """There are rpm repository with local storage present. Leapp is not support such kind of repositories.
\tPlease remove the local repositories to proceed the conversion. Files where locally stored repositories are defined:
\t- {}
"""

    def _is_repo_contains_local_storage(self, repo_file) -> bool:
        with open(repo_file) as f:
            repository_content = f.read()
            return ("baseurl=file:" in repository_content or "baseurl = file:" in repository_content or
                    "metalink=file:" in repository_content or "metalink = file:" in repository_content or
                    "mirrorlist=file:" in repository_content or "mirrorlist = file:" in repository_content)

    def _do_check(self) -> bool:
        # CentOS-Media.repo is a special file which is created by default on CentOS 7. It contains a local repository
        # but leapp allows it anyway. So we could skip it.
        local_repositories_files = [file for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["*.repo"])
                                    if os.path.basename(file) != "CentOS-Media.repo" and self._is_repo_contains_local_storage(file)]

        if len(local_repositories_files) == 0:
            return True

        self.description = self.description.format("\n\t- ".join(local_repositories_files))
        return False


class CheckRepositoryDuplicates(action.CheckAction):
    def __init__(self):
        self.name = "checking if there are duplicate repositories"
        self.description = """There are duplicate repositories present:
\t- {}

\tPlease remove the duplicate to proceed the conversion.
"""

    def _do_check(self) -> bool:
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


class CheckPackagesUpToDate(action.CheckAction):
    def __init__(self):
        self.name = "checking if all packages are up to date"
        self.description = "There are packages which are not up to date. Call `yum update -y && reboot` to update the packages.\n"

    def _do_check(self) -> bool:
        subprocess.check_call(["/usr/bin/yum", "clean", "all"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        checker = subprocess.run(["/usr/bin/yum", "check-update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return checker.returncode == 0
