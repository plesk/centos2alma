from .action import ActiveAction

import os

from common import leapp_configs


class FixupImunify(ActiveAction):
    def __init__(self):
        self.name = "fixing up imunify360"

    def _is_required(self):
        return os.path.exists("/etc/yum.repos.d/imunify360.repo")

    def _prepare_action(self):
        repofiles = []
        for file in os.scandir("/etc/yum.repos.d"):
            if file.name.startswith("imunify") and file.name[-5:] == ".repo":
                repofiles.append(file.path)

        leapp_configs.add_repositories_mapping(repofiles)

        # For some reason leapp replace the libssh2 packageon installation. It's fine in most cases,
        # but imunify packages require libssh2. So we should use PRESENT action to keep it.
        leapp_configs.set_package_action("libssh2", leapp_configs.LeappActionType.PRESENT)

    def _post_action(self):
        pass

    def _revert_action(self):
        pass