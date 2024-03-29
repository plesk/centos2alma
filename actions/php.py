# Copyright 1999 - 2024. WebPros International GmbH. All rights reserved.

import os
import shutil

from common import action, log, packages, php, plesk, systemd, version


class AssertMinPhpVersionInstalled(action.CheckAction):
    min_version: version.PHPVersion

    def __init__(
        self,
        min_version: str,
    ):
        self.name = "check for outdated PHP versions"
        self.min_version = version.PHPVersion(min_version)
        self.description = """Outdated PHP versions were detected: {versions}.
\tRemove outdated PHP packages via Plesk Installer to proceed with the conversion:
\tYou can do it by calling the following command:
\tplesk installer remove --components {remove_arg}
"""

    def _do_check(self) -> bool:
        log.debug(f"Checking for minimum installed PHP version of {self.min_version}")
        # TODO: get rid of the explicit version list
        known_php_versions = php.get_known_php_versions()

        log.debug(f"Known PHP versions: {known_php_versions}")
        outdated_php_versions = [php for php in known_php_versions if php < self.min_version]
        outdated_php_packages = {f"plesk-php{php.major}{php.minor}": str(php) for php in outdated_php_versions}
        log.debug(f"Outdated PHP versions: {outdated_php_versions}")

        installed_pkgs = packages.filter_installed_packages(outdated_php_packages.keys())
        log.debug(f"Outdated PHP packages installed: {installed_pkgs}")
        if len(installed_pkgs) == 0:
            log.debug("No outdated PHP versions installed")
            return True

        self.description = self.description.format(
            versions=", ".join([outdated_php_packages[installed] for installed in installed_pkgs]),
            remove_arg=" ".join(outdated_php_packages[installed].replace(" ", "") for installed in installed_pkgs).lower()
        )

        log.debug("Outdated PHP versions found")
        return False


class AssertMinPhpVersionUsedByWebsites(action.CheckAction):
    min_version: version.PHPVersion

    def __init__(
        self,
        min_version: str,
        optional: bool = True,
    ):
        self.name = "checking domains uses outdated PHP"
        self.min_version = version.PHPVersion(min_version)
        self.optional = optional
        self.description = """We have identified that the domains are using older versions of PHP.
\tSwitch the following domains to {modern} or later in order to continue with the conversion process:
\t- {domains}

\tYou can achieve this by executing the following command:
\t> plesk bin domain -u [domain] -php_handler_id plesk-php80-fastcgi
"""

    def _do_check(self) -> bool:
        log.debug(f"Checking the minimum PHP version being used by the websites. The restriction is: {self.min_version}")
        if not plesk.is_plesk_database_ready():
            if self.optional:
                log.info("Plesk database is not ready. Skipping the minimum PHP for websites check.")
                return True
            raise RuntimeError("Plesk database is not ready. Skipping the minimum PHP for websites check.")

        outdated_php_handlers = [f"'{handler}'" for handler in php.get_outdated_php_handlers(self.min_version)]
        log.debug(f"Outdated PHP handlers: {outdated_php_handlers}")
        try:
            looking_for_domains_sql_request = """
                SELECT d.name FROM domains d JOIN hosting h ON d.id = h.dom_id WHERE h.php_handler_id in ({});
            """.format(", ".join(outdated_php_handlers))

            outdated_php_domains = plesk.get_from_plesk_database(looking_for_domains_sql_request)
            if not outdated_php_domains:
                return True

            log.debug(f"Outdated PHP domains: {outdated_php_domains}")
            outdated_php_domains = "\n\t- ".join(outdated_php_domains)
            self.description = self.description.format(
                modern=self.min_version,
                domains=outdated_php_domains
            )
        except Exception as ex:
            log.err("Unable to get domains list from plesk database!")
            raise RuntimeError("Unable to get domains list from plesk database!") from ex

        return False


class AssertMinPhpVersionUsedByCron(action.CheckAction):
    min_version: version.PHPVersion

    def __init__(
        self,
        min_version: str,
        optional: bool = True,
    ):
        self.name = "checking cronjob uses outdated PHP"
        self.min_version = version.PHPVersion(min_version)
        self.optional = optional
        self.description = """We have detected that some cronjobs are using outdated PHP versions.
\tSwitch the following cronjobs to {modern} or later in order to continue with the conversion process:"
\t- {cronjobs}

\tYou can do this in the Plesk web interface by going “Tools & Settings” → “Scheduled Tasks”.
"""

    def _do_check(self) -> bool:
        log.debug(f"Checking the minimum PHP version used in cronjobs. Restriction is: {self.min_version}")
        if not plesk.is_plesk_database_ready():
            if self.optional:
                log.info("Plesk database is not ready. Skipping the minimum PHP for cronjobs check.")
                return True
            raise RuntimeError("Plesk database is not ready. Skipping the minimum PHP for cronjobs check.")

        outdated_php_handlers = [f"'{handler}'" for handler in php.get_outdated_php_handlers(self.min_version)]
        log.debug(f"Outdated PHP handlers: {outdated_php_handlers}")

        try:
            looking_for_cronjobs_sql_request = """
                SELECT command from ScheduledTasks WHERE type = "php" and phpHandlerId in ({});
            """.format(", ".join(outdated_php_handlers))

            outdated_php_cronjobs = plesk.get_from_plesk_database(looking_for_cronjobs_sql_request)
            if not outdated_php_cronjobs:
                return True

            log.debug(f"Outdated PHP cronjobs: {outdated_php_cronjobs}")
            outdated_php_cronjobs = "\n\t- ".join(outdated_php_cronjobs)

            self.description = self.description.format(
                modern=self.min_version,
                cronjobs=outdated_php_cronjobs)
        except Exception as ex:
            log.err("Unable to get cronjobs list from plesk database!")
            raise RuntimeError("Unable to get cronjobs list from plesk database!") from ex

        return False


class AssertOSVendorPHPUsedByWebsites(action.CheckAction):
    min_version: version.PHPVersion

    def __init__(
            self,
            min_version: str,
    ):
        self.name = "checking OS vendor PHP used by websites"
        self.min_version = version.PHPVersion(min_version)
        self.description = """We have detected that some domains are using the OS vendor PHP version.
\tSwitch the following domains to {modern} or later in order to continue with the conversion process:
\t- {domains}

\tYou can achieve this by executing the following command:
\t> plesk bin domain -u [domain] -php_handler_id plesk-php80-fastcgi
"""

    def _do_check(self) -> bool:
        log.debug("Checking the OS vendor PHP version used by the websites")
        if not plesk.is_plesk_database_ready():
            log.info("Plesk database is not ready. Skipping the OS vendor PHP check.")
            return True

        os_vendor_php_handlers = ["'fpm'", "'fastcgi'"]
        log.debug(f"OS vendor PHP handlers: {os_vendor_php_handlers}")

        try:
            looking_for_domains_sql_request = """
                SELECT d.name FROM domains d JOIN hosting h ON d.id = h.dom_id WHERE h.php_handler_id in ({});
            """.format(", ".join(os_vendor_php_handlers))

            os_vendor_php_domains = plesk.get_from_plesk_database(looking_for_domains_sql_request)
            if not os_vendor_php_domains:
                return True

            log.debug(f"OS vendor PHP domains: {os_vendor_php_domains}")
            os_vendor_php_domains = "\n\t- ".join(os_vendor_php_domains)
            self.description = self.description.format(
                modern=self.min_version,
                domains=os_vendor_php_domains
            )
        except Exception as ex:
            log.err("Unable to get domains list from plesk database!")
            raise RuntimeError("Unable to get domains list from plesk database!") from ex

        return False


OS_VENDOR_PHP_FPM_CONFIG = "/etc/php-fpm.d/www.conf"


class FixOsVendorPhpFpmConfiguration(action.ActiveAction):
    def __init__(self):
        self.name = "fix OS vendor PHP configuration"

    def is_required(self) -> bool:
        if os.path.exists(OS_VENDOR_PHP_FPM_CONFIG):
            return True

    def _prepare_action(self):
        pass

    def _post_action(self):
        # Plesk expect www pool to be disabled by default.
        # Every distro should has the same configuration generated by Plesk.
        # However we store the original configuration in the www.conf.saved_by_psa file.
        if os.path.exists(f"{OS_VENDOR_PHP_FPM_CONFIG}.rpmnew"):
            shutil.move(f"{OS_VENDOR_PHP_FPM_CONFIG}.rpmnew", f"{OS_VENDOR_PHP_FPM_CONFIG}.saved_by_psa")
        elif os.path.exists(f"{OS_VENDOR_PHP_FPM_CONFIG}.rpmsave"):
            shutil.move(f"{OS_VENDOR_PHP_FPM_CONFIG}", f"{OS_VENDOR_PHP_FPM_CONFIG}.saved_by_psa")
            shutil.move(f"{OS_VENDOR_PHP_FPM_CONFIG}.rpmsave", f"{OS_VENDOR_PHP_FPM_CONFIG}")

        if systemd.is_service_exists("php-fpm") and systemd.is_service_active("php-fpm"):
            systemd.restart_services(["php-fpm"])

    def _revert_action(self):
        pass

    def estimate_post_time(self):
        return 1
