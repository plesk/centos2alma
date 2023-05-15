# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.

import os
import subprocess


def send_error_report(error_message):
    # Todo. For now we works only on RHEL-based distros, so the path
    # to the send-error-report utility will be the same.
    # But if we will support Debian-based we should choose path carefully
    send_error_path = "/usr/local/psa/admin/bin/send-error-report"
    try:
        if os.path.exists(send_error_path):
            subprocess.run([send_error_path, "backend"], input=error_message.encode(),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        # We don't care about errors to avoid mislead of the user
        pass
