# Copyright 1999 - 2024. WebPros International GmbH. All rights reserved.
import json
import os
import shutil
import subprocess

from common import action, files, log, motd, plesk, util


class IncreaseDovecotDHParameters(action.ActiveAction):
    def __init__(self):
        self.name = "increase Dovecot DH parameters size to 2048 bits"
        self.dhparam_size = 2048

    def _is_required(self) -> bool:
        proc = subprocess.run(
            ["/usr/sbin/plesk", "sbin", "sslmng", "--show-config"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if proc.returncode != 0:
            log.warn(f"Failed to get ssl configuration by plesk sslmng: {proc.stdout}\n{proc.stderr}")
            return False

        try:
            sslmng_config = json.loads(proc.stdout)
            if int(sslmng_config["effective"]["dovecot"]["dhparams_size"]) >= self.dhparam_size:
                return False
        except json.JSONDecodeError:
            log.warn(f"Failed to parse plesk sslmng results: {proc.stdout}")
            return False

        return True

    def _prepare_action(self) -> None:
        pass

    def _post_action(self) -> None:
        util.logged_check_call(
            [
                "/usr/sbin/plesk", "sbin", "sslmng",
                "--service", "dovecot",
                "--strong-dh",
                f"--dhparams-size={self.dhparam_size}",
            ]
        )

    def _revert_action(self) -> None:
        pass

    def estimate_post_time(self) -> int:
        return 5


class RestoreDovecotConfiguration(action.ActiveAction):
    dovecot_config_path: str

    def __init__(self):
        self.name = "restore Dovecot configuration"
        self.dovecot_config_path = "/etc/dovecot/dovecot.conf"

    def _is_required(self) -> bool:
        return os.path.exists(self.dovecot_config_path)

    def _prepare_action(self) -> None:
        files.backup_file(self.dovecot_config_path)

    def _post_action(self):
        path_to_backup = plesk.CONVERTER_TEMP_DIRECTORY + "/dovecot.conf.bak"
        if os.path.exists(self.dovecot_config_path):
            shutil.copy(path_to_backup, self.dovecot_config_path)
            motd.add_finish_ssh_login_message(f"The dovecot configuration '{self.dovecot_config_path}' has been restored from CentOS 7. Modern configuration was placed in '{path_to_backup}'.")

        files.restore_file_from_backup(self.dovecot_config_path)

    def _revert_action(self):
        files.remove_backup(self.dovecot_config_path)
