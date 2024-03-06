# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
from common import action, files, leapp_configs, log, motd, plesk, rpm, util

import os
import shutil


class RemovingPleskConflictPackages(action.ActiveAction):

    def __init__(self):
        self.name = "remove plesk conflict packages"
        self.conflict_pkgs = [
            "openssl11-libs",
            "python36-PyYAML",
            "GeoIP",
            "psa-mod_proxy",
        ]

    def _prepare_action(self):
        rpm.remove_packages(rpm.filter_installed_packages(self.conflict_pkgs))

    def _post_action(self):
        pass

    def _revert_action(self):
        rpm.install_packages(self.conflict_pkgs)

    def estimate_prepare_time(self):
        return 2

    def estimate_revert_time(self):
        return 10


class ReinstallPleskComponents(action.ActiveAction):
    def __init__(self):
        self.name = "re-installing plesk components"

    def _prepare_action(self):
        components_pkgs = [
            "plesk-roundcube",
            "psa-phpmyadmin",
        ]

        rpm.remove_packages(rpm.filter_installed_packages(components_pkgs))

    def _post_action(self):
        # We should reinstall psa-phpmyadmin over plesk installer to make sure every trigger
        # will be called. It's because triggers that creates phpmyadmin configuration files
        # expect plesk on board. Hence when we install the package in scope of temporary OS
        # the file can't be created.
        rpm.remove_packages(["psa-phpmyadmin"])
        util.logged_check_call(["/usr/sbin/plesk", "installer", "update"])

        util.logged_check_call(["/usr/sbin/plesk", "installer", "add", "--components", "roundcube"])

    def _revert_action(self):
        util.logged_check_call(["/usr/sbin/plesk", "installer", "update"])
        util.logged_check_call(["/usr/sbin/plesk", "installer", "add", "--components", "roundcube"])

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        return 2 * 60

    def estimate_revert_time(self):
        return 6 * 60


class ReinstallConflictPackages(action.ActiveAction):
    def __init__(self):
        self.name = "re-installing common conflict packages"
        self.removed_packages_file = plesk.CONVERTER_TEMP_DIRECTORY + "/centos2alma_removed_packages.txt"
        self.conflict_pkgs_map = {
            "galera": "galera",
            "python36-argcomplete": "python3-argcomplete",
            "python36-cffi": "python3-cffi",
            "python36-chardet": "python3-chardet",
            "python36-colorama": "python3-colorama",
            "python36-cryptography": "python3-cryptography",
            "python36-pycurl": "python3-pycurl",
            "python36-dateutil": "python3-dateutil",
            "python36-dbus": "python3-dbus",
            "python36-decorator": "python3-decorator",
            "python36-gobject-base": "python3-gobject-base",
            "python36-idna": "python3-idna",
            "python36-jinja2": "python3-jinja2",
            "python36-jsonschema": "python3-jsonschema",
            "python36-jwt": "python3-jwt",
            "python36-lxml": "python3-lxml",
            "python36-markupsafe": "python3-markupsafe",
            "python36-pyOpenSSL": "python3-pyOpenSSL",
            "python36-ply": "python3-ply",
            "python36-prettytable": "python3-prettytable",
            "python36-pycparser": "python3-pycparser",
            "python36-pyparsing": "python3-pyparsing",
            "python36-pyserial": "python3-pyserial",
            "python36-pytz": "python3-pytz",
            "python36-requests": "python3-requests",
            "python36-six": "python3-six",
            "python36-urllib3": "python3-urllib3",
            "libpcap": "libpcap",
            "libwebp7": "libwebp",
            "libzip5": "libzip",
            "libytnef": "ytnef",
        }

    def _is_required(self):
        return len(rpm.filter_installed_packages(self.conflict_pkgs_map.keys())) > 0

    def _prepare_action(self):
        packages_to_remove = rpm.filter_installed_packages(self.conflict_pkgs_map.keys())

        rpm.remove_packages(packages_to_remove)

        with open(self.removed_packages_file, "w") as f:
            f.write("\n".join(packages_to_remove))

    def _post_action(self):
        if not os.path.exists(self.removed_packages_file):
            log.warn("File with removed packages list is not exists. While the action itself was not skipped. Skip reinstalling packages.")
            return

        with open(self.removed_packages_file, "r") as f:
            packages_to_install = [self.conflict_pkgs_map[pkg] for pkg in f.read().splitlines()]
            rpm.install_packages(packages_to_install)

        os.unlink(self.removed_packages_file)

    def _revert_action(self):
        if not os.path.exists(self.removed_packages_file):
            log.warn("File with removed packages list is not exists. While the action itself was not skipped. Skip reinstalling packages.")
            return

        with open(self.removed_packages_file, "r") as f:
            packages_to_install = f.read().splitlines()
            rpm.install_packages(packages_to_install)

        os.unlink(self.removed_packages_file)

    def estimate_prepare_time(self):
        return 10

    def estimate_post_time(self):
        pkgs_number = 0
        if os.path.exists(self.removed_packages_file):
            with open(self.removed_packages_file, "r") as f:
                pkgs_number = len(f.read().splitlines())
        return 60 + 10 * pkgs_number

    def estimate_revert_time(self):
        pkgs_number = 0
        if os.path.exists(self.removed_packages_file):
            with open(self.removed_packages_file, "r") as f:
                pkgs_number = len(f.read().splitlines())
        return 60 + 10 * pkgs_number


class UpdatePlesk(action.ActiveAction):
    def __init__(self):
        self.name = "updating plesk"

    def _prepare_action(self):
        # The conversion process removes the python36-lxml package since it conflicts with python3-lxml from AlmaLinux.
        # If the conversion fails for any reason and there is no rollback, we need to reinstall the package.
        # Otherwise, the Plesk installer will encounter issues. The problem with conversion only occurs when
        # new Plesk packages have been published, such as hotfixes, so the impact of the problem is low.
        # However, because we don't do a rollback for every conversion failure, this scenario is possible
        # and could be confusing for users. Therefore, we've decided to handle it proactively.
        if not rpm.is_package_installed("python36-lxml"):
            rpm.install_packages(["python36-lxml"])

        util.logged_check_call(["/usr/sbin/plesk", "installer", "update"])

    def _post_action(self):
        pass

    def _revert_action(self):
        pass

    def estimate_prepare_time(self):
        return 3 * 60


CHANGED_REPOS_MSG_FMT = """During the conversion, some of customized .repo files were updated. You can find the old
files with the .rpmsave extension. Below is a list of the changed files:
\t{changed_files}
"""


class AdoptRepositories(action.ActiveAction):
    def __init__(self):
        self.name = "adopting repositories"

    def _prepare_action(self):
        pass

    def _use_rpmnew_repositories(self):
        # The problem is about changed repofiles, that leapp tring to install form packages.
        # For example, when epel.repo file was changed, dnf will save the new one as epel.repo.rpmnew. 
        # I beleive there could be other files with the same problem, so lets iterate every .rpmnew file in /etc/yum.repos.d
        fixed_list = rpm.handle_all_rpmnew_files("/etc/yum.repos.d")

        if len(fixed_list) > 0:
            motd.add_finish_ssh_login_message(CHANGED_REPOS_MSG_FMT.format(changed_files="\n\t".join(fixed_list)))

    def _adopt_plesk_repositories(self):
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*.repo"]):
            rpm.remove_repositories(file, [
                lambda id, _1, _2, _3: id in ["PLESK_17_PHP52", "PLESK_17_PHP53",
                                              "PLESK_17_PHP54", "PLESK_17_PHP55",
                                              "PLESK_17_PHP56", "PLESK_17_PHP70"],
            ])
            leapp_configs.adopt_repositories(file)

    def _post_action(self):
        self._use_rpmnew_repositories()
        self._adopt_plesk_repositories()
        util.logged_check_call(["/usr/bin/dnf", "-y", "update"])

    def _revert_action(self):
        pass

    def estimate_post_time(self):
        return 2 * 60


class RemoveOldMigratorThirparty(action.ActiveAction):
    def __init__(self):
        self.name = "removing old migrator thirdparty packages"

    def _is_required(self):
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*migrator*.repo"]):
            for _1, _2, url, _3, _4 in rpm.extract_repodata(file):
                if "PMM_0.1.10/thirdparty-rpm" in url:
                    return True

        return False

    def _prepare_action(self):
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*migrator*.repo"]):
            files.backup_file(file)

            rpm.remove_repositories(file, [
                lambda _1, _2, baseurl, _3: "PMM_0.1.10/thirdparty-rpm" in baseurl,
            ])

    def _post_action(self):
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*migrator*.repo"]):
            files.remove_backup(file)

    def _revert_action(self):
        for file in files.find_files_case_insensitive("/etc/yum.repos.d", ["plesk*migrator*.repo"]):
            files.restore_file_from_backup(file)


class RestoreMissingNginx(action.ActiveAction):
    def __init__(self):
        self.name = "restore nginx if it was removed during the conversion"

    def _is_required(self):
        # nginx related to plesk could be removed by user. So we need to make sure
        # it is installed before we start the conversion
        return rpm.is_package_installed("sw-nginx")

    def _prepare_action(self):
        pass

    def _post_action(self):
        if not rpm.is_package_installed("sw-nginx"):
            util.logged_check_call(["/usr/sbin/plesk", "installer", "add", "--components", "nginx"])

    def _revert_action(self):
        pass

    def estimate_post_time(self):
        return 3 * 60


class CheckOutdatedLetsencryptExtensionRepository(action.CheckAction):
    OUTDATED_LETSENCRYPT_REPO_PATHS = ["/etc/yum.repos.d/plesk-letsencrypt.repo", "/etc/yum.repos.d/plesk-ext-letsencrypt.repo"]

    def __init__(self):
        self.name = "checking if outdated repository for letsencrypt extension is used"
        self.description = """There is outdated repository for letsencrypt extension used.
\tTo resolve the problem perform following actions:
\t1. make sure the letsencrypt extension is up to date from Plesk web interface
\t2. rpm -qe plesk-letsencrypt-pre plesk-py27-pip plesk-py27-setuptools plesk-py27-virtualenv plesk-wheel-cffi plesk-wheel-cryptography plesk-wheel-psutil
\t3. rm {repo_paths}
"""

    def _do_check(self):
        for path in self.OUTDATED_LETSENCRYPT_REPO_PATHS:
            if os.path.exists(path):
                self.description = self.description.format(repo_paths=path)
                return False
        return True
