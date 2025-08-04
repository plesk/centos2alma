# Copyright 1999 - 2025. Plesk International GmbH. All rights reserved.

import collections
import os
import platform
import shutil
import subprocess

from pleskdistup.common import action, dist, files, log, version


# Todo. Action is not relevant now, because we checking the same thing of framework side
# Additionaly platrofm module has no linux_distribution method in modern version of python
# so we should migrate to our common.distro
class AssertDistroIsCentos79(action.CheckAction):
    def __init__(self):
        self.name = "checking if distro is CentOS7"
        self.description = """You are running a distribution other than CentOS 7.9. At the moment, only CentOS 7.9 is supported.
\tIf you are running an earlier Centos 7 release, update to Centos 7.9 and try again.
"""

    def _do_check(self) -> bool:
        distro = platform.linux_distribution()
        major_version, minor_version = distro[1].split(".")[:2]
        if distro[0] == "CentOS Linux" and int(major_version) == 7 and int(minor_version) == 9:
            return True
        return False


class AssertDistroIsAlmalinux8(action.CheckAction):
    def __init__(self):
        self.name = "checking if distro is AlmaLinux8"
        self.description = "You are running a distribution other than AlmaLinux 8. The finalization stage can only be started on AlmaLinux 8."

    def _do_check(self) -> bool:
        return dist.get_distro() == dist.AlmaLinux("8")


class AssertNoMoreThenOneKernelNamedNIC(action.CheckAction):
    def __init__(self):
        self.name = "checking if there is more than one NIC interface using kernel-name"
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


# ToDo. Implement for deb-based and move to common part. Might be useful for distupgrade/other converters
class AssertLastInstalledKernelInUse(action.CheckAction):
    no_kernel_installed_message: str = """There is no appropriate kernel package installed.
\tTo proceed with the conversion, install a kernel by running: 'yum install kernel kernel-tools kernel-tools-libs'
"""

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

        if not versions:
            return None

        log.debug("Installed kernel versions: {}".format(', '.join(versions)))
        versions = [version.KernelVersion(ver) for ver in versions]
        return max(versions)

    def _do_check(self) -> bool:
        last_installed_kernel_version = self._get_last_installed_kernel_version()
        if not last_installed_kernel_version:
            self.description = self.no_kernel_installed_message
            return False

        used_kernel_version = self._get_kernel_version_in_use()

        if used_kernel_version != last_installed_kernel_version:
            self.description = self.description.format(str(used_kernel_version), str(last_installed_kernel_version))
            return False

        return True


class AssertRedHatKernelInstalled(action.CheckAction):
    def __init__(self):
        self.name = "checking if the Red Hat kernel is installed"
        self.description = """No Red Hat signed kernel is installed.
\tTo proceed with the conversion, install a kernel by running:
\t- 'yum install kernel kernel-tools kernel-tools-libs'
\tAfter installing the kernel fix the grub configuration by calling:
\t- `grub2-set-default 'CentOS Linux (newly_installed_kernel_version) 7 (Core)'`
\t- `grub2-mkconfig -o /boot/grub2/grub.cfg`
\t- `reboot`
"""

    def _do_check(self) -> bool:
        redhat_kernel_packages = subprocess.check_output(
            [
                "/usr/bin/rpm", "-q", "-a", "kernel", "kernel-rt"
            ], universal_newlines=True
        ).splitlines()
        return len(redhat_kernel_packages) > 0


class AssertLocalRepositoryNotPresent(action.CheckAction):
    def __init__(self):
        self.name = "checking if the local repository is present"
        self.description = """There are rpm repository with local storage present. Leapp does support such kind of repositories.
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


class AssertThereIsNoRepositoryDuplicates(action.CheckAction):
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


class AssertPackagesUpToDate(action.CheckAction):
    def __init__(self):
        self.name = "checking if all packages are up to date"
        self.description = "There are packages which are not up to date. Call `yum update -y && reboot` to update the packages.\n"

    def _do_check(self) -> bool:
        subprocess.check_call(["/usr/bin/yum", "clean", "all"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        checker = subprocess.run(["/usr/bin/yum", "check-update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return checker.returncode == 0


class AssertAvailableSpaceForLocation(action.CheckAction):
    def __init__(self, location: str, required_space: int):
        self.name = f"checking available space for {location}"
        self.location = location
        self.required_space = required_space
        self.description = """There is insufficient disk space available. Leapp requires a minimum of {} of free space
\ton the disk where the '{}' directory is located. Available space: {}.
\tFree up enough disk space and try again.
"""

    def _huminize_size(self, size) -> str:
        original = size
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{original} B"

    def _do_check(self) -> bool:
        if not os.path.exists(self.location):
            self.description = f"The leapp required location '{self.location}' does not exist. To proceed with the conversion, create the directory."
            return False

        available_space = shutil.disk_usage(self.location)[2]
        if available_space >= self.required_space:
            return True

        self.description = self.description.format(self._huminize_size(self.required_space), self.location, self._huminize_size(available_space))
        return False


class AssertNoAbsoluteLinksInRoot(action.CheckAction):
    def __init__(self):
        self.name = "checking there are no absolute links in the root directory"
        self.description = """Absolute links are present in the root directory. Leapp does not support absolute links in '/'.
\tFrom leapp source: "After rebooting, parts of the upgrade process can fail if symbolic links in point to absolute paths."
\tTo proceed with the conversion, change the links to relative ones for following files:
\t- {}
"""

    def _do_check(self) -> bool:
        absolute_links = []
        for directory in os.listdir('/'):
            dirpath = os.path.join('/', directory)
            if os.path.islink(dirpath):
                target = os.readlink(dirpath)
                if os.path.isabs(target):
                    absolute_links.append(dirpath)

        if len(absolute_links) == 0:
            return True

        self.description = self.description.format("\n\t- ".join(absolute_links))
        return False
