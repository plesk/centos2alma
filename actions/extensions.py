from .action import ActiveAction

import os
import pwd
import shutil

from common import util, log


# We should do rebundling of ruby applications after the conversion
# because some of our libraries will be missing.
# The prime example of missing library - libmysqlclient.so.18 required by mysql2 gem
class RebundleRubyApplications(ActiveAction):
    def __init__(self):
        self.name = "rebundling ruby applications"
        self.description = "rebundling ruby applications"

    def _find_file_in_domain(self, domain, file):
        for root, _, files in os.walk(domain):
            for subfile in files:
                if os.path.basename(subfile) == file:
                    return os.path.join(root, file)
        return None

    def _find_directory_in_domain(self, domain, directory):
        for root, directories, _ in os.walk(domain):
            for subdir in directories:
                if os.path.basename(subdir) == directory:
                    return os.path.join(root, directory)
        return None

    def _is_ruby_domain(self, domain_path):
        return os.path.exists(os.path.join(domain_path, ".rbenv"))

    def _is_required(self):
        if not os.path.exists("/var/lib/rbenv/versions/"):
            return False

        return any(self._is_ruby_domain(domain) for domain in os.scandir("/var/www/vhosts"))

    def _prepare_action(self):
        pass

    def _post_action(self):
        ruby_domains = (domain_path for domain_path in os.scandir("/var/www/vhosts") if self._is_ruby_domain(domain_path))
        for domain_path in ruby_domains:
            log.debug("Rebundling ruby application in domain: {}".format(domain_path.name))

            boundle = self._find_directory_in_domain(domain_path, "bundle")
            if boundle is None or not os.path.isdir(boundle):
                log.debug("Skip reboundling for non boundled domain '{}'".format(domain_path.name))
                continue

            app_directory = os.path.dirname(os.path.dirname(boundle))
            stat_info = os.stat(boundle)
            username = pwd.getpwuid(stat_info.st_uid).pw_name

            log.debug("Boundle: {}. App directory: {}. Username: {}".format(boundle, app_directory, username))

            shutil.rmtree(boundle)
            util.logged_check_call(["plesk", "sbin", "rubymng", "run-bundler", username, app_directory])

    def _revert_action(self):
        pass

    def estimate_post_time(self):
        return 60 * len([domain_path for domain_path in os.scandir("/var/www/vhosts") if self._is_ruby_domain(domain_path)])
