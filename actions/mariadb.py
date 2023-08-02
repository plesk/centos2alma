# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction

import subprocess
import os

from common import leapp_configs, files, log, rpm, util


MARIADB_VERSION_ON_ALMA = "10.3.35"


def _is_version_larger(left: str, right: str) -> bool:
    for pleft, pright in zip(left.split("."), right.split(".")):
        if int(pleft) > int(pright):
            return True
        elif int(pright) > int(pleft):
            return False

    return False


def _get_mariadb_utilname() -> str:
    for utility in ("mariadb", "mysql"):
        if subprocess.run(["which", utility], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return utility

    return None


def _is_mariadb_installed() -> bool:
    utility = _get_mariadb_utilname()
    if utility is None:
        return False
    elif utility == "mariadb":
        return True

    return "MariaDB" in subprocess.check_output([utility, "--version"], universal_newlines=True)


def _is_mysql_installed() -> bool:
    utility = _get_mariadb_utilname()
    if utility is None or utility == "mariadb":
        return False

    return "MariaDB" not in subprocess.check_output([utility, "--version"], universal_newlines=True)


def _get_mariadb_version() -> str:
    utility = _get_mariadb_utilname()

    out = subprocess.check_output([utility, "--version"], universal_newlines=True)

    log.debug("Detected mariadb version is: {version}".format(version=out.split("Distrib ")[1].split(",")[0].split("-")[0]))

    return out.split("Distrib ")[1].split(",")[0].split("-")[0]


class UpdateModernMariadb(ActiveAction):
    def __init__(self):
        self.name = "update modern mariadb"

    def _is_required(self) -> bool:
        return _is_mariadb_installed() and _is_version_larger(_get_mariadb_version(), MARIADB_VERSION_ON_ALMA)

    def _prepare_action(self) -> None:
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["mariadb.repo"])
        if len(repofiles) == 0:
            raise Exception("Mariadb installed from unknown repository. Please check the '{}' file is present".format("/etc/yum.repos.d/mariadb.repo"))

        leapp_configs.add_repositories_mapping(repofiles)
        leapp_configs.set_package_repository("mariadb", "alma-maridb")

    def _post_action(self) -> None:
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["mariadb.repo"])
        if len(repofiles) == 0:
            return 0

        for repofile in repofiles:
            leapp_configs.adopt_repositories(repofile)

        rpm.remove_packages(rpm.filter_installed_packages(["MariaDB-client",
                                                           "MariaDB-compat",
                                                           "MariaDB-common",
                                                           "MariaDB-server",
                                                           "MariaDB-shared"]))
        rpm.install_packages(["MariaDB-client", "MariaDB-server"], repository="alma-mariadb")

    def _revert_action(self) -> None:
        pass

    def estimate_prepare_time(self) -> int:
        return 30

    def estimate_post_time(self) -> int:
        return 60


class UpdateMariadbDatabase(ActiveAction):
    def __init__(self):
        self.name = "updating mariadb databases"

    def _is_required(self) -> bool:
        return _is_mariadb_installed() and not _is_version_larger(_get_mariadb_version(), MARIADB_VERSION_ON_ALMA)

    def _prepare_action(self) -> None:
        pass

    def _post_action(self) -> None:
        # Leapp is not remove non-standard MariaDB-client package. But since we have updated
        # mariadb to 10.3.35 old client is not relevant anymore. So we have to switch to new client.
        # On the other hand we want to be sure AlmaLinux mariadb-server installed as well
        for repofile in files.find_files_case_insensitive("/etc/yum.repos.d", ["mariadb.repo"]):
            files.backup_file(repofile)
            os.unlink(repofile)

        rpm.remove_packages(rpm.filter_installed_packages(["MariaDB-client",
                                                           "MariaDB-compat",
                                                           "MariaDB-common",
                                                           "MariaDB-server",
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

    def _revert_action(self) -> None:
        pass

    def estimate_post_time(self):
        return 2 * 60


class AddMysqlConnector(ActiveAction):
    def __init__(self):
        self.name = "install mysql connector"

    def _is_required(self) -> bool:
        return _is_mysql_installed()

    def _prepare_action(self) -> None:
        pass

    def _post_action(self) -> None:
        subprocess.check_call(["/usr/bin/dnf", "install", "-y", "mariadb-connector-c"])

    def _revert_action(self) -> None:
        pass
