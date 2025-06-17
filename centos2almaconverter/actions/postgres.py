# Copyright 1999 - 2025. Plesk International GmbH. All rights reserved.
import locale
import os
import subprocess

from pleskdistup.common import action, files, leapp_configs, log, postgres, systemd, util

_ALMA8_POSTGRES_VERSION = 10


class AssertOutdatedPostgresNotInstalled(action.CheckAction):
    def __init__(self):
        self.name = "checking postgres version 10 or later is installed"
        self.description = '''Postgres version less then 10. This means the database should be upgraded.
\tIt might leads to data lose. Please make backup of your database and call the script with --upgrade-postgres.
\tOr update postgres to version 10 and upgrade your databases.'''

    def _do_check(self):
        return not postgres.is_postgres_installed() or not postgres.is_database_initialized() or not postgres.is_database_major_version_lower(_ALMA8_POSTGRES_VERSION)


class AssertPostgresLocaleMatchesSystemOne(action.CheckAction):
    def __init__(self):
        self.name = "checking if system locale is safe for Postgres databases upgrade"
        self.description = """Postgres database upgrade expects system locale to match the one databases were created with.
\tYou may need to change system locale (see /etc/locale.conf and the locale command) or
\tdatcollate and datctype properties of Postgres databases to match each other."""
        self.service_name = 'postgresql'

    def _do_check(self):
        if not systemd.is_service_exists(self.service_name):
            log.debug(f"Postgres service {self.service_name} does not exist. Skip system locale for postgresql pre-check.")
            return False

        config_path = os.path.join(postgres.get_data_path(), 'pg_hba.conf')

        try:
            files.backup_file(config_path)
            files.push_front_strings(config_path, ["local template1 postgres trust #Added by Plesk\n"])
            util.logged_check_call(['systemctl', 'reload-or-restart', self.service_name])

            query = "SELECT datcollate, datctype FROM pg_database WHERE datname='postgres';"
            cmd = ['/usr/bin/psql', '-U', 'postgres', '-d', 'template1', '-qt', '-v', 'ON_ERROR_STOP=1', '-P', 'border=0']
            pg_locales = set(subprocess.check_output(cmd, input=query, universal_newlines=True).split())
            if len(pg_locales) != 1:
                log.debug(f"Got unexpected Postgres locales set: {pg_locales!r}")
                return False

            sys_locales = set(l.split('=')[1].strip() for l in files.find_file_substrings('/etc/locale.conf', 'LANG='))
            env_locale = locale.getlocale()
            if env_locale and env_locale[0]:
                sys_locales.add('.'.join(map(str, env_locale)))

            if len(sys_locales) != 1:
                log.debug(f"Got unexpected system locales set: {sys_locales!r}")
                return False

            log.debug(f"Postgres locale is {pg_locales!r}, system locale is {sys_locales!r}")
            return pg_locales == sys_locales
        finally:
            files.restore_file_from_backup(config_path)
            util.logged_check_call(['systemctl', 'reload-or-try-restart', self.service_name])


class PostgresDatabasesUpdate(action.ActiveAction):

    def __init__(self):
        self.name = "updating postgres databases"
        self.service_name = 'postgresql'

    def _is_required(self):
        return postgres.is_postgres_installed() and postgres.is_database_initialized() and postgres.is_database_major_version_lower(_ALMA8_POSTGRES_VERSION)

    def _prepare_action(self) -> action.ActionResult:
        util.logged_check_call(['systemctl', 'stop', self.service_name])
        util.logged_check_call(['systemctl', 'disable', self.service_name])
        return action.ActionResult()

    def _upgrade_database(self):
        util.logged_check_call(['dnf', 'install', '-y', 'postgresql-upgrade'])

        util.logged_check_call(['postgresql-setup', '--upgrade'])

        old_config_path = os.path.join(postgres.get_saved_data_path(), 'pg_hba.conf')
        new_config_path = os.path.join(postgres.get_data_path(), 'pg_hba.conf')

        plesk_customizations = []
        with open(old_config_path, 'r') as old_config:
            plesk_customizations = [line for line in old_config.readlines() if '#Added by Plesk' in line]

        files.push_front_strings(new_config_path, plesk_customizations)

        util.logged_check_call(['dnf', 'remove', '-y', 'postgresql-upgrade'])

    def _enable_postgresql(self):
        util.logged_check_call(['systemctl', 'enable', self.service_name])
        util.logged_check_call(['systemctl', 'start', self.service_name])

    def _post_action(self) -> action.ActionResult:
        self._upgrade_database()
        self._enable_postgresql()
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        self._enable_postgresql()
        return action.ActionResult()

    def estimate_post_time(self):
        return 3 * 60


class PostgresReinstallModernPackage(action.ActiveAction):
    # Leapp is going to remove postgresql package from the system during conversion process.
    # So during this action we shouldn't use any postgresql related commands. Luckily data will not be removed
    # and we can use them to recognize versions of postgresql we should install.
    def __init__(self):
        self.name = "reinstall modern postgresql"

    def _get_versions(self):
        return [int(dataset) for dataset in os.listdir(postgres.get_pgsql_root_path()) if dataset.isnumeric()]

    def _is_required(self):
        return postgres.is_postgres_installed() and any([major_version >= _ALMA8_POSTGRES_VERSION for major_version in self._get_versions()])

    def _is_service_active(self, service):
        res = subprocess.run(['/usr/bin/systemctl', 'is-active', service])
        return res.returncode == 0

    def _prepare_action(self) -> action.ActionResult:
        leapp_configs.add_repositories_mapping(["/etc/yum.repos.d/pgdg-redhat-all.repo"])

        for major_version in self._get_versions():
            service_name = 'postgresql-' + str(major_version)
            if self._is_service_active(service_name):
                with open(os.path.join(postgres.get_pgsql_root_path(), str(major_version)) + '.enabled', 'w') as fp:
                    pass
                util.logged_check_call(['/usr/bin/systemctl', 'stop', service_name])
                util.logged_check_call(['/usr/bin/systemctl', 'disable', service_name])

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for major_version in self._get_versions():
            if major_version > _ALMA8_POSTGRES_VERSION:
                util.logged_check_call(['/usr/bin/dnf', '-q', '-y', 'module', 'disable', 'postgresql'])
                util.logged_check_call(['/usr/bin/dnf', 'update'])
                util.logged_check_call(['/usr/bin/dnf', 'install', "-y", 'postgresql' + str(major_version), 'postgresql' + str(major_version) + '-server'])
            else:
                util.logged_check_call(['/usr/bin/dnf', '-q', '-y', 'module', 'enable', 'postgresql'])
                util.logged_check_call(['/usr/bin/dnf', 'update'])
                util.logged_check_call(['/usr/bin/dnf', 'install', "-y", 'postgresql', 'postgresql' + '-server'])

            if os.path.exists(os.path.join(postgres.get_pgsql_root_path(), str(major_version) + '.enabled')):
                service_name = 'postgresql-' + str(major_version)
                util.logged_check_call(['/usr/bin/systemctl', 'enable', service_name])
                util.logged_check_call(['/usr/bin/systemctl', 'start', service_name])
                os.remove(os.path.join(postgres.get_pgsql_root_path(), str(major_version) + '.enabled'))

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for major_version in self._get_versions():
            if os.path.exists(os.path.join(postgres.get_pgsql_root_path(), str(major_version) + '.enabled')):
                service_name = 'postgresql-' + str(major_version)
                util.logged_check_call(['/usr/bin/systemctl', 'stop', service_name])
                util.logged_check_call(['/usr/bin/systemctl', 'disable', service_name])
                os.remove(os.path.join(postgres.get_pgsql_root_path(), str(major_version) + '.enabled'))

        return action.ActionResult()

    def estimate_post_time(self):
        return 3 * 60
