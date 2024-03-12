# Copyright 1999 - 2024. WebPros International GmbH. All rights reserved.
import json
import subprocess

from common import action, log, util


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
