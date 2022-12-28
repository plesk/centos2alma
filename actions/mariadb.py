from .action import ActivaAction

import subprocess
import os
# import json

from common import leapp_configs
from common import log


class AvoidMariadbDowngrade(ActivaAction):
    def __init__(self):
        self.name = "avoid instalation old mariadb"
        self.mariadb_version_on_alma = "10.3.35"
        self.mariadb_repofile = "/etc/yum.repos.d/mariadb.repo"

    def _is_version_larger(self, left, right):
        for pleft, pright in zip(left.split("."), right.split(".")):
            if int(pleft) > int(pright):
                return True
            elif int(pright) > int(pleft):
                return False

        return False

    def _is_mariadb_installed(self):
        return subprocess.run(["which", "mariadb"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    def _get_mariadb_version(self):
        process = subprocess.Popen(["mariadb", "--version"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True)
        out, err = process.communicate()
        if process.returncode != 0:
            raise RuntimeError("Unable to get mariadb version: {}".format(err))

        log.debug("Detected mariadb version is: {version}".format(version=out.split("Distrib ")[1].split(",")[0].split("-")[0]))

        return out.split("Distrib ")[1].split(",")[0].split("-")[0]

    def _is_required(self):
        return self._is_mariadb_installed() and not self._is_version_larger(self.mariadb_version_on_alma, self._get_mariadb_version())

    def _prepare_action(self):
        if not os.path.exists(self.mariadb_repofile):
            raise Exception("Mariadb installed from unknown repository. Please check the '{}' file is present".format(self.mariadb_repofile))

        log.debug("Going to add mariadb repository '{repofile}'".format(repofile=self.mariadb_repofile))
        leapp_configs.add_repositories_mapping([self.mariadb_repofile])

        # with open("/etc/leapp/files/pes-events.json", "r") as pkg_mapping_file:
        #     pkg_mapping = json.load(pkg_mapping_file)
        #     for info in pkg_mapping["packageinfo"]:

    def _post_action(self):
        pass


class UpdateMariadbDatabase(ActivaAction):
    def __init__(self):
        self.name = "fixing mariadb databases"

    def _prepare_action(self):
        pass

    def _post_action(self):
        # We should be sure mariadb is started, otherwise restore woulden't work
        subprocess.check_call(["systemctl", "start", "mariadb"])

        with open('/etc/psa/.psa.shadow', 'r') as shadowfile:
            shadowdata = shadowfile.readline().rstrip()
            subprocess.check_call(["mysql_upgrade", "-uadmin", "-p" + shadowdata])
        # Also find a way to drop cookies, because it will ruin your day
        # Redelete it, because leapp going to install it in scoupe of convertation process, but it will no generate right configs
