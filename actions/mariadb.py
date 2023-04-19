# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction

import subprocess
import os

from common import leapp_configs, files, log, rpm, util


MARIADB_VERSION_ON_ALMA = "10.3.35"


def _is_version_larger(left, right):
    for pleft, pright in zip(left.split("."), right.split(".")):
        if int(pleft) > int(pright):
            return True
        elif int(pright) > int(pleft):
            return False

    return False


def _get_mariadb_utilname():
    for utility in ("mariadb", "mysql"):
        if subprocess.run(["which", utility], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return utility

    return None


def _is_mariadb_installed():
    utility = _get_mariadb_utilname()
    if utility is None:
        return False
    elif utility == "mariadb":
        return True

    return "MariaDB" in subprocess.check_output([utility, "--version"], universal_newlines=True)


def _is_mysql_installed():
    utility = _get_mariadb_utilname()
    if utility is None or utility == "mariadb":
        return False

    return "MariaDB" not in subprocess.check_output([utility, "--version"], universal_newlines=True)


def _get_mariadb_version():
    utility = _get_mariadb_utilname()

    out = subprocess.check_output([utility, "--version"], universal_newlines=True)

    log.debug("Detected mariadb version is: {version}".format(version=out.split("Distrib ")[1].split(",")[0].split("-")[0]))

    return out.split("Distrib ")[1].split(",")[0].split("-")[0]


class AvoidMariadbDowngrade(ActiveAction):
    def __init__(self):
        self.name = "avoid mariadb downgrade"

    def _is_required(self):
        return _is_mariadb_installed() and not _is_version_larger(MARIADB_VERSION_ON_ALMA, _get_mariadb_version())

    def _prepare_action(self):
        repofiles = files.find_files_case_insensitive("/etc/yum.repos.d", ["mariadb.repo"])
        if len(repofiles) == 0:
            raise Exception("Mariadb installed from unknown repository. Please check the '{}' file is present".format("/etc/yum.repos.d/mariadb.repo"))

        leapp_configs.add_repositories_mapping(repofiles)
        leapp_configs.set_package_repository("mariadb", "alma-maridb")

    def _post_action(self):
        pass

    def _revert_action(self):
        pass


class UpdateMariadbDatabase(ActiveAction):
    def __init__(self):
        self.name = "updating mariadb databases"

    def _is_required(self):
        return _is_mariadb_installed() and _is_version_larger(MARIADB_VERSION_ON_ALMA, _get_mariadb_version())

    def _prepare_action(self):
        pass

    def _post_action(self):
        # Leapp is not remove non-standart MariaDB-client package. But since we have updated
        # mariadb to 10.3.35 old client is not relevant anymore. So we have to switch to new client
        rpm.remove_packages(rpm.filter_installed_packages(["MariaDB-client", "MariaDB-common", "MariaDB-shared"]))
        rpm.install_packages(["mariadb"])

        # We should be sure mariadb is started, otherwise restore woulden't work
        util.logged_check_call(["/usr/bin/systemctl", "start", "mariadb"])

        with open('/etc/psa/.psa.shadow', 'r') as shadowfile:
            shadowdata = shadowfile.readline().rstrip()
            util.logged_check_call(["/usr/bin/mysql_upgrade", "-uadmin", "-p" + shadowdata])
        # Also find a way to drop cookies, because it will ruin your day
        # We have to delete it once again, because leapp going to install it in scope of conversation process,
        # but without right configs

    def _revert_action(self):
        pass

    def estimate_post_time(self):
        return 2 * 60


class AddMysqlConnector(ActiveAction):
    def __init__(self):
        self.name = "install mysql connector"

    def _is_required(self):
        return _is_mysql_installed()

    def _prepare_action(self):
        pass

    def _post_action(self):
        subprocess.check_call(["/usr/bin/dnf", "install", "-y", "mariadb-connector-c"])

    def _revert_action(self):
        pass
