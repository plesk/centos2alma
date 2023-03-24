# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from .action import ActiveAction, CheckAction

import os
import subprocess
import shutil

from common import leapp_configs
from common import util

_PATH_TO_PGSQL = '/var/lib/pgsql'
_PATH_TO_DATA = os.path.join(_PATH_TO_PGSQL, 'data')
_PATH_TO_OLD_DATA = os.path.join(_PATH_TO_PGSQL, 'data-old')
_MODERN_POSTGRES = 10


def _is_postgres_installed():
    return os.path.exists(_PATH_TO_PGSQL)


def _get_postgres_major_version():
    version_out = subprocess.check_output(['psql', '--version'], universal_newlines=True)
    return int(version_out.split(' ')[2].split('.')[0])


def _is_database_initialized():
    return os.path.exists(os.path.join(_PATH_TO_DATA, "PG_VERSION"))


def _is_modern_database():
    version_file_path = os.path.join(_PATH_TO_DATA, "PG_VERSION")

    if not os.path.exists(version_file_path):
        raise Exception('There is no "' + version_file_path + '" file')

    with open(version_file_path, 'r') as version_file:
        version = int(version_file.readline().split('.')[0])
        if version >= _MODERN_POSTGRES:
            return True


class CheckOutdatedPostgresInstalled(CheckAction):
    def __init__(self):
        self.name = "checking postgres version 10 or later is installed"
        self.description = '''Postgres version less then 10. This means the database should be upgraded.
\tIt might leads to data lose. Please make backup of your database and call the script with --upgrade-postgres.
\tOr update postgres to version 10 and upgrade your databases.'''

    def _do_check(self):
        return not _is_postgres_installed() or not _is_database_initialized() or _get_postgres_major_version() >= _MODERN_POSTGRES


class PostgresDatabasesUpdate(ActiveAction):

    def __init__(self):
        self.name = "updating postgres databases"
        self.service_name = 'postgresql'

    def _is_required(self):
        return _is_postgres_installed() and _is_database_initialized() and not _is_modern_database()

    def _prepare_action(self):
        util.logged_check_call(['systemctl', 'stop', self.service_name])
        util.logged_check_call(['systemctl', 'disable', self.service_name])

    def _upgrade_database(self):
        util.logged_check_call(['dnf', 'install', '-y', 'postgresql-upgrade'])

        util.logged_check_call(['postgresql-setup', '--upgrade'])

        old_config_path = os.path.join(_PATH_TO_OLD_DATA, 'pg_hba.conf')
        new_config_path = os.path.join(_PATH_TO_DATA, 'pg_hba.conf')
        next_config_path = os.path.join(_PATH_TO_DATA, 'pg_hba.conf.next')

        plesk_customizations = []
        with open(old_config_path, 'r') as old_config:
            plesk_customizations = [line for line in old_config.readlines() if '#Added by Plesk']

        with open(next_config_path, "w") as dst:
            for customization in plesk_customizations:
                dst.write(customization)

            with open(new_config_path, "r") as original:
                for line in original.readlines():
                    dst.write(line)

        shutil.move(next_config_path, new_config_path)

        util.logged_check_call(['dnf', 'remove', '-y', 'postgresql-upgrade'])

    def _enable_postgresql(self):
        util.logged_check_call(['systemctl', 'enable', self.service_name])
        util.logged_check_call(['systemctl', 'start', self.service_name])

    def _post_action(self):
        self._upgrade_database()
        self._enable_postgresql()

    def _revert_action(self):
        self._enable_postgresql()

    def estimate_post_time(self):
        return 3 * 60


class PostgresReinstallModernPackage(ActiveAction):
    # Leapp is going to remove postgresql package from the system during conversion process.
    # So during this action we shouldn't use any postgresql related commands. Luckily data will not be removed
    # and we can use them to recognize versions of postgresql we should install.
    def __init__(self):
        self.name = "reinstall modern postgresql"

    def _get_versions(self):
        return [int(dataset) for dataset in os.listdir(_PATH_TO_PGSQL) if dataset.isnumeric()]

    def _is_required(self):
        return _is_postgres_installed() and any([major_version >= _MODERN_POSTGRES for major_version in self._get_versions()])

    def _is_service_active(self, service):
        res = subprocess.run(['systemctl', 'is-active', service])
        return res.returncode == 0

    def _prepare_action(self):
        leapp_configs.add_repositories_mapping(["/etc/yum.repos.d/pgdg-redhat-all.repo"])

        for major_version in self._get_versions():
            service_name = 'postgresql-' + str(major_version)
            if self._is_service_active(service_name):
                with open(os.path.join(_PATH_TO_PGSQL, str(major_version)) + '.enabled', 'w') as fp:
                    pass
                util.logged_check_call(['systemctl', 'stop', service_name])
                util.logged_check_call(['systemctl', 'disable', service_name])

    def _post_action(self):
        for major_version in self._get_versions():
            if major_version > _MODERN_POSTGRES:
                util.logged_check_call(['dnf', '-q', '-y', 'module', 'disable', 'postgresql'])
                util.logged_check_call(['dnf', 'update'])
                util.logged_check_call(['dnf', 'install', "-y", 'postgresql' + str(major_version), 'postgresql' + str(major_version) + '-server'])
            else:
                util.logged_check_call(['dnf', '-q', '-y', 'module', 'enable', 'postgresql'])
                util.logged_check_call(['dnf', 'update'])
                util.logged_check_call(['dnf', 'install', "-y", 'postgresql', 'postgresql' + '-server'])

            if os.path.exists(os.path.join(_PATH_TO_PGSQL, str(major_version) + '.enabled')):
                service_name = 'postgresql-' + str(major_version)
                util.logged_check_call(['systemctl', 'enable', service_name])
                util.logged_check_call(['systemctl', 'start', service_name])
                os.remove(os.path.join(_PATH_TO_PGSQL, str(major_version) + '.enabled'))

    def _revert_action(self):
        for major_version in self._get_versions():
            if os.path.exists(os.path.join(_PATH_TO_PGSQL, str(major_version) + '.enabled')):
                service_name = 'postgresql-' + str(major_version)
                util.logged_check_call(['systemctl', 'stop', service_name])
                util.logged_check_call(['systemctl', 'disable', service_name])
                os.remove(os.path.join(_PATH_TO_PGSQL, str(major_version) + '.enabled'))

    def estimate_post_time(self):
        return 3 * 60
