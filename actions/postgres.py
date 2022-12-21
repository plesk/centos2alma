from .action import Action

import os
import subprocess
import shutil


class PostgresDatabasesUpdate(Action):

    PATH_TO_PGSQL = '/var/lib/pgsql'
    PATH_TO_DATA = os.path.join(PATH_TO_PGSQL, 'data')
    PATH_TO_OLD_DATA = os.path.join(PATH_TO_PGSQL, 'data-old')

    def __init__(self):
        self.name = "update postgre databases"
        self.service_name = 'postgresql'

    def _is_postgres_installed(self):
        return os.path.exists(self.PATH_TO_DATA)

    def _is_required(self):
        return self._is_postgres_installed()

    def _prepare_action(self):
        subprocess.check_call(['systemctl', 'stop', self.service_name])
        subprocess.check_call(['systemctl', 'disable', self.service_name])

    def _is_database_modern_version(self):
        version_file_path = os.path.join(self.PATH_TO_DATA, "PG_VERSION")

        if not os.path.exists(version_file_path):
            raise Exception('There is no "' + version_file_path + '" file')

        with open(version_file_path, 'r') as version_file:
            version = int(version_file.readline().split('.')[0])
            if version >= 10:
                return True

        return False

    def _upgrade_database(self):
        if self._is_database_modern_version():
            return

        subprocess.check_call(['dnf', 'install', '-y', 'postgresql-upgrade'])

        subprocess.check_call(['postgresql-setup', '--upgrade'])

        old_config_path = os.path.join(self.PATH_TO_OLD_DATA, 'pg_hba.conf')
        new_config_path = os.path.join(self.PATH_TO_DATA, 'pg_hba.conf')
        next_config_path = os.path.join(self.PATH_TO_DATA, 'pg_hba.conf.next')

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

        subprocess.check_call(['dnf', 'remove', '-y', 'postgresql-upgrade'])

    def _enable_postgresql(self):
        subprocess.check_call(['systemctl', 'enable', self.service_name])
        subprocess.check_call(['systemctl', 'start', self.service_name])

    def _post_action(self):
        self._upgrade_database()
        self._enable_postgresql()
