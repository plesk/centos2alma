# Copyright 1999 - 2024. Plesk International GmbH. All rights reserved.
import subprocess
import os

from pleskdistup.common import action, leapp_configs, files, log, mariadb, rpm, util


MARIADB_VERSION_ON_ALMA = mariadb.MariaDBVersion("10.3.39")
KNOWN_MARIADB_REPO_FILES = [
    "mariadb.repo",
    "mariadb10.repo",
]


class AssertMariadbRepoAvailable(action.CheckAction):
    def __init__(self):
        self.name = "check mariadb repo available"
        self.description = """
The MariaDB repository with id '{}' from the file '{}' is not accessible.
\tThis issue may be caused by the deprecation of the currently installed MariaDB version or the disabling
\tof the MariaDB repository by the provider. To resolve this, update MariaDB to any version from the official
\trepository 'rpm.mariadb.org', or use the official archive repository for your current MariaDB version at 'archive.mariadb.org'.
"""

    def _do_check(self) -> bool:
        if not mariadb.is_mariadb_installed() or not mariadb.get_installed_mariadb_version() > MARIADB_VERSION_ON_ALMA:
            return True

        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", KNOWN_MARIADB_REPO_FILES)
        if len(repofiles) == 0:
            return True

        for repofile in repofiles:
            for repo in rpm.extract_repodata(repofile):
                repo_id, _, repo_baseurl, _, _, _ = repo
                if not repo_baseurl or ".mariadb.org" not in repo_baseurl:
                    continue

                # Since repository will be deprecated for any distro at once it looks fine to check only for 7 on x86_64
                repo_baseurl = repo_baseurl.replace("$releasever", "7").replace("$basearch", "x86_64")
                result = subprocess.run(["curl", "-s", "-o", "/dev/null", "-f", repo_baseurl])
                if result.returncode != 0:
                    self.description = self.description.format(repo_id, repofile)
                    return False

        return True


class UpdateModernMariadb(action.ActiveAction):
    def __init__(self):
        self.name = "update modern mariadb"

    def _is_required(self) -> bool:
        return mariadb.is_mariadb_installed() and mariadb.get_installed_mariadb_version() > MARIADB_VERSION_ON_ALMA

    def _prepare_action(self) -> action.ActionResult:
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", KNOWN_MARIADB_REPO_FILES)
        if len(repofiles) == 0:
            raise Exception("Mariadb installed from unknown repository. Please check the '{}' file is present".format("/etc/yum.repos.d/mariadb.repo"))

        log.debug("Add MariaDB repository files '{}' mapping".format(repofiles[0]))
        leapp_configs.add_repositories_mapping(repofiles)

        log.debug("Set repository mapping in the leapp configuration file")
        leapp_configs.set_package_repository("mariadb", "alma-mariadb")
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", KNOWN_MARIADB_REPO_FILES)
        if len(repofiles) == 0:
            return action.ActionResult()

        for repofile in repofiles:
            leapp_configs.adopt_repositories(repofile)

        mariadb_repo_id, _1, _2, _3, _4, _5 = [repo for repo in rpm.extract_repodata(repofiles[0])][0]

        rpm.remove_packages(rpm.filter_installed_packages(["MariaDB-client",
                                                           "MariaDB-client-compat",
                                                           "MariaDB-compat",
                                                           "MariaDB-common",
                                                           "MariaDB-server",
                                                           "MariaDB-server-compat",
                                                           "MariaDB-shared"]))
        rpm.install_packages(["MariaDB-client", "MariaDB-server"], repository=mariadb_repo_id)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 30

    def estimate_post_time(self) -> int:
        return 60


class UpdateMariadbDatabase(action.ActiveAction):
    def __init__(self):
        self.name = "updating mariadb databases"

    def _is_required(self) -> bool:
        return mariadb.is_mariadb_installed() and not mariadb.get_installed_mariadb_version() > MARIADB_VERSION_ON_ALMA

    def _prepare_action(self) -> action.ActionResult:
        rpm.remove_packages(rpm.filter_installed_packages(["MariaDB-client",
                                                           "MariaDB-client-compat",
                                                           "MariaDB-compat",
                                                           "MariaDB-common",
                                                           "MariaDB-server",
                                                           "MariaDB-server-compat",
                                                           "MariaDB-shared"]))
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        # Leapp is not remove non-standard MariaDB-client package. But since we have updated
        # mariadb to 10.3.35 old client is not relevant anymore. So we have to switch to new client.
        # On the other hand we want to be sure AlmaLinux mariadb-server installed as well
        for repofile in files.find_files_case_insensitive("/etc/yum.repos.d", KNOWN_MARIADB_REPO_FILES):
            files.backup_file(repofile)
            os.unlink(repofile)

        rpm.remove_packages(rpm.filter_installed_packages(["MariaDB-client",
                                                           "MariaDB-client-compat",
                                                           "MariaDB-compat",
                                                           "MariaDB-common",
                                                           "MariaDB-server",
                                                           "MariaDB-server-compat",
                                                           "MariaDB-shared"]))
        rpm.install_packages(["mariadb", "mariadb-server"])

        # We should be sure mariadb is started, otherwise restore woulden't work
        util.logged_check_call(["/usr/bin/systemctl", "start", "mariadb"])

        with open('/etc/psa/.psa.shadow', 'r') as shadowfile:
            shadowdata = shadowfile.readline().rstrip()
            util.logged_check_call(["/usr/bin/mysql_upgrade", "-uadmin", "-p" + shadowdata])
        # Also find a way to drop cookies, because it will ruin your day
        # We have to delete it once again, because leapp going to install it in scope of conversion process,
        # but without right configs
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self):
        return 2 * 60


class AddMysqlConnector(action.ActiveAction):
    def __init__(self):
        self.name = "install mysql connector"

    def _is_required(self) -> bool:
        return mariadb.is_mysql_installed()

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        subprocess.check_call(["/usr/bin/dnf", "install", "-y", "mariadb-connector-c"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()
