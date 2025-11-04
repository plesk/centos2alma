# Copyright 1999 - 2025. Plesk International GmbH. All rights reserved.
import os
import typing
import shutil
import subprocess
import re

from pleskdistup.common import action, files, leapp_configs, log, motd, packages, plesk, rpm, systemd, util
from pleskdistup.upgrader import PathType


class RemovingPleskConflictPackages(action.ActiveAction):

    def __init__(self):
        self.name = "remove plesk conflict packages"
        self.conflict_pkgs = [
            "openssl11-libs",
            "python36-PyYAML",
            "GeoIP",
            "psa-mod_proxy",
        ]

    def _prepare_action(self) -> action.ActionResult:
        packages.remove_packages(rpm.filter_installed_packages(self.conflict_pkgs))
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        packages.install_packages(self.conflict_pkgs)
        return action.ActionResult()

    def estimate_prepare_time(self):
        return 2

    def estimate_revert_time(self):
        return 10


class RemovePleskOutdatedPackages(action.ActiveAction):
    outdated_pkgs: typing.List[str]

    def __init__(self) -> None:
        self.name = "remove plesk outdated packages"
        self.outdated_pkgs = [
            "psa-fileserver",
        ]

    def _prepare_action(self) -> action.ActionResult:
        packages.remove_packages(rpm.filter_installed_packages(self.outdated_pkgs))
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        # This packages are outdated so they not provided by modern Plesk repositories
        # So we can't reinstall them on revert, and seems like there is no need to do that anyway
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 2


class ReinstallPhpmyadminPleskComponents(action.ActiveAction):
    def __init__(self):
        self.name = "re-installing plesk components"

    def _prepare_action(self) -> action.ActionResult:
        components_pkgs = [
            "psa-phpmyadmin",
        ]

        packages.remove_packages(rpm.filter_installed_packages(components_pkgs))
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        # We should reinstall psa-phpmyadmin over plesk installer to make sure every trigger
        # will be called. It's because triggers that creates phpmyadmin configuration files
        # expect plesk on board. Hence when we install the package in scope of temporary OS
        # the file can't be created.
        phpmyadmin_package_name: str = "psa-phpmyadmin"
        if packages.is_package_installed(phpmyadmin_package_name):
            packages.remove_packages([phpmyadmin_package_name])

        util.logged_check_call(["/usr/sbin/plesk", "installer", "update"])

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/sbin/plesk", "installer", "update"])
        systemd.restart_services(["sw-cp-server"])
        return action.ActionResult()

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        return 60

    def estimate_revert_time(self):
        return 3 * 60


class ReinstallRoundcubePleskComponents(action.ActiveAction):
    def __init__(self):
        self.name = "re-installing roundcube plesk components"

    def is_required(self) -> bool:
        return plesk.is_component_installed("roundcube")

    def _prepare_action(self) -> action.ActionResult:
        packages.remove_packages(rpm.filter_installed_packages(["plesk-roundcube"]))
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/sbin/plesk", "installer", "add", "--components", "roundcube"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/sbin/plesk", "installer", "add", "--components", "roundcube"])
        systemd.restart_services(["sw-cp-server"])
        return action.ActionResult()

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        return 60

    def estimate_revert_time(self):
        return 3 * 60


class ReinstallConflictPackages(action.ActiveAction):
    removed_packages_file: str
    conflict_pkgs_map: typing.Dict[str, str]

    def __init__(self, temp_directory: str):
        self.name = "re-installing common conflict packages"
        self.removed_packages_file = temp_directory + "/centos2alma_removed_packages.txt"
        self.conflict_pkgs_map = {
            "galera": "galera",
            "python36-argcomplete": "python3-argcomplete",
            "python36-cffi": "python3-cffi",
            "python36-chardet": "python3-chardet",
            "python36-colorama": "python3-colorama",
            "python36-cryptography": "python3-cryptography",
            "python36-pycurl": "python3-pycurl",
            "python36-dateutil": "python3-dateutil",
            "python36-dbus": "python3-dbus",
            "python36-decorator": "python3-decorator",
            "python36-gobject-base": "python3-gobject-base",
            "python36-idna": "python3-idna",
            "python36-jinja2": "python3-jinja2",
            "python36-jsonschema": "python3-jsonschema",
            "python36-jwt": "python3-jwt",
            "python36-lxml": "python3-lxml",
            "python36-markupsafe": "python3-markupsafe",
            "python36-pyOpenSSL": "python3-pyOpenSSL",
            "python36-ply": "python3-ply",
            "python36-prettytable": "python3-prettytable",
            "python36-pycparser": "python3-pycparser",
            "python36-pyparsing": "python3-pyparsing",
            "python36-pyserial": "python3-pyserial",
            "python36-pytz": "python3-pytz",
            "python36-requests": "python3-requests",
            "python36-six": "python3-six",
            "python36-urllib3": "python3-urllib3",
            "libpcap": "libpcap",
            "libwebp7": "libwebp",
            "libzip5": "libzip",
            "libytnef": "ytnef",
            "lua-socket": "lua-socket",
        }

    def _is_required(self):
        return len(rpm.filter_installed_packages(self.conflict_pkgs_map.keys())) > 0

    def _prepare_action(self) -> action.ActionResult:
        packages_to_remove = rpm.filter_installed_packages(list(self.conflict_pkgs_map.keys()))

        rpm.remove_packages(packages_to_remove)

        with open(self.removed_packages_file, "a") as f:
            f.write("\n".join(packages_to_remove) + "\n")

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        if not os.path.exists(self.removed_packages_file):
            log.warn("File with removed packages list is not exists. While the action itself was not skipped. Skip reinstalling packages.")
            return action.ActionResult()

        with open(self.removed_packages_file, "r") as f:
            packages_to_install = [self.conflict_pkgs_map[pkg] for pkg in set(f.read().splitlines())]
            rpm.install_packages(packages_to_install)

        os.unlink(self.removed_packages_file)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        if not os.path.exists(self.removed_packages_file):
            log.warn("File with removed packages list is not exists. While the action itself was not skipped. Skip reinstalling packages.")
            return action.ActionResult()

        with open(self.removed_packages_file, "r") as f:
            packages_to_install = list(set(f.read().splitlines()))
            rpm.install_packages(packages_to_install)

        os.unlink(self.removed_packages_file)
        return action.ActionResult()

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        pkgs_number = 0
        if os.path.exists(self.removed_packages_file):
            with open(self.removed_packages_file, "r") as f:
                pkgs_number = len(f.read().splitlines())
        return 60 + 10 * pkgs_number

    def estimate_revert_time(self):
        pkgs_number = 0
        if os.path.exists(self.removed_packages_file):
            with open(self.removed_packages_file, "r") as f:
                pkgs_number = len(f.read().splitlines())
        return 60 + 10 * pkgs_number


class FixEpelPythonPackageMappings(action.ActiveAction):
    """Update EPEL package mappings for python-webtest and python-webob packages
    This is required because default mapping force leapp to install python2 versions of these packages
    which is broken on AlmaLinux 8:
    - python2-webob does not provided by any repository
    - python2-webtest depends on python2-webob
    The action could be disabled, when problem will be fixed from AlmaLinux side.
    """

    def __init__(self, target_config=leapp_configs.LEAPP_EPEL_MAPPING_PATH):
        self.name = "updating EPEL package mappings for leapp"
        self.target_config = target_config

    def _is_required(self) -> bool:
        if not os.path.exists(self.target_config):
            return False

        installed_packages = rpm.filter_installed_packages(['python-webtest', 'python-webob'])
        return len(installed_packages) > 0

    def _prepare_action(self) -> action.ActionResult:
        files.backup_file(self.target_config)

        leapp_configs.set_package_mapping(
            in_package="python-webtest",
            source_repository="epel",
            out_package="python3-webtest",
            target_repository="el8-epel",
            leapp_pkgs_conf_path=self.target_config
        )

        leapp_configs.set_package_mapping(
            in_package="python-webob",
            source_repository="base",
            out_package="python3-webob",
            target_repository="el8-epel",
            leapp_pkgs_conf_path=self.target_config
        )

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        if os.path.exists(self.target_config):
            files.remove_backup(self.target_config)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        if os.path.exists(self.target_config):
            files.restore_file_from_backup(self.target_config)
        return action.ActionResult()

    def estimate_prepare_time(self):
        return 5

    def estimate_post_time(self):
        return 2

    def estimate_revert_time(self):
        return 2



CHANGED_REPOS_MSG_FMT = """During the conversion, some of customized .repo files were updated. You can find the old
files with the .rpmsave extension. Below is a list of the changed files:
\t{changed_files}
"""


class AdoptRepositories(action.ActiveAction):
    def __init__(self):
        self.name = "adopting repositories"

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _use_rpmnew_repositories(self):
        # The problem is about changed repofiles, that leapp tring to install form packages.
        # For example, when epel.repo file was changed, dnf will save the new one as epel.repo.rpmnew.
        # I beleive there could be other files with the same problem, so lets iterate every .rpmnew file in /etc/yum.repos.d
        fixed_list = []
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["*.rpmnew"]):
            original_file = file[:-len(".rpmnew")]
            if os.path.exists(original_file):
                shutil.move(original_file, original_file + ".rpmsave")
                fixed_list.append(original_file)

            shutil.move(file, original_file)

        if len(fixed_list) > 0:
            motd.add_finish_ssh_login_message(CHANGED_REPOS_MSG_FMT.format(changed_files="\n\t".join(fixed_list)))

    def _adopt_plesk_repositories(self):
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*.repo"]):
            rpm.remove_repositories(file, [
                lambda repo: repo.id in ["PLESK_17_PHP52", "PLESK_17_PHP53",
                                         "PLESK_17_PHP54", "PLESK_17_PHP55"],
            ])
            leapp_configs.adopt_repositories(file)

    def _post_action(self) -> action.ActionResult:
        self._use_rpmnew_repositories()
        self._adopt_plesk_repositories()
        util.logged_check_call(["/usr/bin/dnf", "-y", "update"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self):
        return 2 * 60


class AdoptRackspaceEpelRepository(action.ActiveAction):
    epel_repository_file_path: str = "/etc/yum.repos.d/epel.repo"

    def __init__(self):
        self.name = "adopting rackspace epel repository"

    def _is_rackspace_epel_repo(self, repo_file: PathType) -> bool:
        for repo in rpm.extract_repodata(repo_file):
            if repo.url and "iad.mirror.rackspace.com" in repo.url:
                return True
        return False

    def is_required(self) -> bool:
        return os.path.exists(self.epel_repository_file_path) and self._is_rackspace_epel_repo(self.epel_repository_file_path)

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        leapp_configs.adopt_repositories(self.epel_repository_file_path, keep_id=True)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class AssertPleskRepositoriesNotNoneLink(action.CheckAction):
    def __init__(self):
        self.name = "checking if plesk repositories are adoptable"
        self.description = """There are plesk repositories has none link. To proceed the conversion, remove following repositories:
\t- {}
"""

    def _do_check(self) -> bool:
        none_link_repos = []
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*.repo"]):
            for repo in rpm.extract_repodata(file):
                if rpm.repository_has_none_link(repo):
                    none_link_repos.append(f"{repo.id!r} from repofile {file!r}")

        if len(none_link_repos) == 0:
            return True

        self.description = self.description.format("\n\t- ".join(none_link_repos))
        return False


class AssertIPRepositoryNotPresent(action.CheckAction):
    def __init__(self):
        self.name = "verify the presence of a repository sourced from an IP address"
        self.description = """There is an RPM repository from a source host with an IP address.
\tWe cannot confirm if this repository's packages conflict with AlmaLinux's official repositories.
\tTo proceed with the conversion, please remove the repositories listed in the following .repo files:
\t- {}
"""

    def _is_repo_source_ip_address(self, repo_file) -> bool:
        for repo in rpm.extract_repodata(repo_file):
            if rpm.repository_source_is_ip(repo):
                return True
        return False

    def _do_check(self) -> bool:
        ip_source_repositories_files = [file for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["*.repo"])
                                        if self._is_repo_source_ip_address(file)]

        if len(ip_source_repositories_files) == 0:
            return True

        self.description = self.description.format("\n\t- ".join(ip_source_repositories_files))
        return False


class AssertCentosEOLedRepositoriesNotPresent(action.CheckAction):
    def __init__(self):
        self.name = "verify there is no EOL-ed CentOS 7 repository"
        self.description = """A deprecated CentOS 7 repository was found.
\tTo continue with the conversion, please replace the repositories listed in the following .repo files with vault repositories, such as vault.centos.org:
\t- {}
"""

    def _is_repository_enabled(self, repository_additional_info: typing.List[str]) -> bool:
        for line in repository_additional_info:
            if line.startswith("enabled="):
                return line.split("=")[1].strip() == "1"
        return True

    def _is_repo_source_eoled(self, repo_file) -> bool:
        for repo in rpm.extract_repodata(repo_file):
            if not self._is_repository_enabled(repo.additional):
                log.debug("Skip disabled repository '{}'".format(repo.id))
                continue

            if repo.mirrorlist and repo.mirrorlist.startswith("http://mirrorlist.centos.org/"):
                log.debug("Found depricated repository '{}' with mirrorlist '{}'".format(repo.id, repo.mirrorlist))
                return True

            if repo.url and repo.url.startswith("http://mirror.centos.org/centos"):
                log.debug("Found depricated repository '{}' with baseurl '{}'".format(repo.id, repo.url))
                return True
        return False

    def _do_check(self) -> bool:
        ip_source_repositories_files = [file for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["*.repo"])
                                        if self._is_repo_source_eoled(file)]

        if len(ip_source_repositories_files) == 0:
            return True

        self.description = self.description.format("\n\t- ".join(ip_source_repositories_files))
        return False


class RemoveOldMigratorThirparty(action.ActiveAction):
    def __init__(self):
        self.name = "removing old migrator thirdparty packages"

    def _is_required(self) -> bool:
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*migrator*.repo"]):
            for repo in rpm.extract_repodata(file):
                if repo.url and "PMM_0.1.10/thirdparty-rpm" in repo.url:
                    return True

        return False

    def _prepare_action(self) -> action.ActionResult:
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*migrator*.repo"]):
            files.backup_file(file)

            rpm.remove_repositories(file, [
                lambda repo: (repo.url is not None and "PMM_0.1.10/thirdparty-rpm" in repo.url),
            ])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*migrator*.repo"]):
            files.remove_backup(file)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*migrator*.repo"]):
            files.restore_file_from_backup(file)
        return action.ActionResult()


class RestoreMissingNginx(action.ActiveAction):
    def __init__(self):
        self.name = "restore nginx if it was removed during the conversion"

    def _is_required(self) -> bool:
        # nginx related to plesk could be removed by user. So we need to make sure
        # it is installed before we start the conversion
        return packages.is_package_installed("sw-nginx")

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        if not packages.is_package_installed("sw-nginx"):
            util.logged_check_call(["/usr/sbin/plesk", "installer", "add", "--components", "nginx"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self):
        return 3 * 60


class CheckOutdatedLetsencryptExtensionRepository(action.CheckAction):
    OUTDATED_LETSENCRYPT_REPO_PATHS = ["/etc/yum.repos.d/plesk-letsencrypt.repo", "/etc/yum.repos.d/plesk-ext-letsencrypt.repo"]

    def __init__(self):
        self.name = "checking if outdated repository for letsencrypt extension is used"
        self.description = """There is outdated repository for letsencrypt extension used.
\tTo resolve the problem perform following actions:
\t1. make sure the letsencrypt extension is up to date from Plesk web interface
\t2. rpm -qe plesk-letsencrypt-pre plesk-py27-pip plesk-py27-setuptools plesk-py27-virtualenv plesk-wheel-cffi plesk-wheel-cryptography plesk-wheel-psutil
\t3. rm {repo_paths}
"""

    def _do_check(self) -> bool:
        for path in self.OUTDATED_LETSENCRYPT_REPO_PATHS:
            if os.path.exists(path):
                self.description = self.description.format(repo_paths=path)
                return False
        return True


class AdoptAtomicRepositories(action.ActiveAction):
    atomic_repository_path: str = "/etc/yum.repos.d/tortix-common.repo"

    def __init__(self):
        self.name = "adopting atomic repositories"

    def is_required(self) -> bool:
        return os.path.exists(self.atomic_repository_path)

    def _prepare_action(self) -> action.ActionResult:
        leapp_configs.add_repositories_mapping([self.atomic_repository_path])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        # We don't need to adopt repositories here because repositories uses $releasever-$basearch
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()


class CheckSourcePointsToArchiveURL(action.CheckAction):
    AUTOINSTALLERRC_PATH = os.path.expanduser('~/.autoinstallerrc')

    def __init__(self):
        self.name = "checking if SOURCE points to old archive"
        self.description = f"""Old archive doesn't serve up-to-date Plesk.
\tEdit {self.AUTOINSTALLERRC_PATH} and change SOURCE - i.e. https://autoinstall.plesk.com
""".format(self)

    def _do_check(self) -> bool:
        if not os.path.exists(self.AUTOINSTALLERRC_PATH):
            return True
        p = re.compile(r'^\s*SOURCE\s*=\s*https?://autoinstall-archives.plesk.com')
        with open(self.AUTOINSTALLERRC_PATH) as f:
            for line in f:
                if p.search(line):
                    return False
        return True


class HandleInternetxRepository(action.ActiveAction):
    KNOWN_INTERNETX_REPO_FILES = ["internetx.repo"]

    def __init__(self):
        self.name = "handling InternetX repository"

    def is_required(self) -> bool:
        return len(files.find_files_case_insensitive("/etc/yum.repos.d", self.KNOWN_INTERNETX_REPO_FILES)) > 0

    def _prepare_action(self) -> action.ActionResult:
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", self.KNOWN_INTERNETX_REPO_FILES):
            files.backup_file(file)
            leapp_configs.add_repositories_mapping([file])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", self.KNOWN_INTERNETX_REPO_FILES):
            files.remove_backup(file)
            leapp_configs.adopt_repositories(file)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", self.KNOWN_INTERNETX_REPO_FILES):
            files.restore_file_from_backup(file)
        return action.ActionResult()


class AssertCentosSignedKernelInstalled(action.CheckAction):
    def __init__(self):
        self.name = "checking if CentOS signed kernel is installed"
        self.description = """There is no kernel packages signed by CentOS installed.
\tTo proceed with the conversion, please install the kernel from official CentoOS repository.
"""

    def _get_pgp_key_id(self, file_path: str) -> typing.Optional[str]:
        try:
            output = subprocess.check_output(["/usr/bin/gpg", "--list-packets", file_path], universal_newlines=True)
            for line in output.splitlines():
                line = line.strip()
                if line.startswith("keyid: "):
                    return line.split(": ")[1].lower()
        except Exception as e:
            log.err(f"Failed to get PGP key ID from {file_path}: {e}")
        return None

    def _signed_by_one_of_keys(self, package_description: str, keys: typing.Set[str]) -> bool:
        for key_id in keys:
            if key_id in package_description:
                return True
        return False

    def _do_check(self) -> bool:
        # You could find the same list at centos/gpg-signatures.json in leapp-repository
        # Unfortunately leapp is not installed at this moment so we have to create set of id's manually
        known_pgp_keys_ids: typing.Set[str] = set([
            "24c6a8a7f4a80eb5",
            "05b555b38483c65d",
            "4eb84e71f2ee9d55",
            "429785e181b961a5",
            "d07bf2a08d50eb66",
            "6c7cb6ef305d49d6"
        ])

        default_key_path = "/etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7"
        if os.path.exists(default_key_path):
            default_key_id = self._get_pgp_key_id(default_key_path)
            if default_key_id is not None:
                known_pgp_keys_ids.add(default_key_id)
        try:
            packages_with_pgpsig = subprocess.check_output(["/usr/bin/rpm", "-q", "--queryformat", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH} %{SIGPGP:pgpsig}\n", "kernel"], universal_newlines=True)
        except subprocess.CalledProcessError as e:
            log.err(f"Failed to get kernel package information: {e}")
            # The reason likely is not the same as described in the pre-checker description
            # So if we will show the message to user, they will be confused. So we just skip the pre-check
            return True

        if packages_with_pgpsig.startswith("package kernel is not installed"):
            # This means that kernel package is not installed. It is generally expected that a kernel package is present.
            # And this action designed to check a little other problem, so description message can be misleading.
            # So it's better to use another action to catch such kind of problem. Currently we use AssertRedHatKernelInstalled
            log.warn(f"Kernel package is not installed. Skipping the {self.__class__.__name__} precheck.")
            return True

        return any(self._signed_by_one_of_keys(pkg, known_pgp_keys_ids) for pkg in packages_with_pgpsig.splitlines() if pkg)


class DisablePleskTechMirrorRepositories(action.ActiveAction):
    """Disable base and update repositories from base.repo if they use mirror.pp.plesk.tech.
        The repositories have packages that conflict with AlmaLinux packages so we have to disable them.
    """
    base_repo_path: str = "/etc/yum.repos.d/base.repo"
    plesk_mirror_url_substring: str = "mirror.pp.plesk.tech"

    def __init__(self):
        self.name = "disabling plesk tech mirror repositories"

    def is_required(self) -> bool:
        if not os.path.exists(self.base_repo_path):
            return False

        for repo in rpm.extract_repodata(self.base_repo_path):
            if repo.id in ["base", "updates"] and repo.url and self.plesk_mirror_url_substring in repo.url:
                return True
        return False

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        if not os.path.exists(self.base_repo_path):
            log.warn(f"Repository file {self.base_repo_path} does not exist. Skipping.")
            return action.ActionResult()

        disabled_repos = rpm.disable_repo_if(
            self.base_repo_path,
            lambda repo: (repo.id in ["base", "updates"] and
                          repo.url and self.plesk_mirror_url_substring in repo.url)
        )

        for repo_id in disabled_repos:
            log.info(f"Disabled repository '{repo_id}' in {self.base_repo_path} because it uses {self.plesk_mirror_url_substring}.")

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self):
        return 5


class HandleCentosExtrasRepositoriesFromExtensions(action.ActiveAction):
    def __init__(self):
        self.name = "handling CentOS related extras repositories installed by plesk extensions"

    def is_required(self) -> bool:
        """Required only when there are any *-extras.repo files with [extras] repository"""
        extras_files = files.find_files_case_insensitive("/etc/yum.repos.d", ["*-extras.repo"])

        for repo_file in extras_files:
            try:
                for repo in rpm.extract_repodata(repo_file):
                    if repo.id == "extras":
                        return True
            except (FileNotFoundError, ValueError):
                continue

        return False

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for repo_file in files.find_files_case_insensitive("/etc/yum.repos.d", ["*-extras.repo"]):
            try:
                repos_in_file = list(rpm.extract_repodata(repo_file))

                files.backup_file(repo_file)
                if len(repos_in_file) == 1 and repos_in_file[0].id == "extras":
                    os.remove(repo_file)
                    log.info(f"Removed {repo_file} with outdated [extras] repository")
                else:
                    disabled_repo = rpm.disable_repo_if(
                        repo_file,
                        lambda repo: repo.id == "extras"
                    )
                    if disabled_repo:
                        log.info(f"Disabled [extras] repository in {repo_file}")
                    else:
                        files.remove_backup(repo_file)
            except (FileNotFoundError, ValueError) as e:
                log.warn(f"Could not process repository file {repo_file}: {e}")
                continue

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self):
        return 10
