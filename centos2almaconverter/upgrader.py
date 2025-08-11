# Copyright 1999-2025. Plesk International GmbH. All rights reserved.

import argparse
import json
import os
import pkg_resources
import typing
import sys

from centos2almaconverter import actions as centos2alma_actions
from pleskdistup import actions as common_actions
from pleskdistup.common import action, dist, feedback, files, php, util, version
from pleskdistup.phase import Phase
from pleskdistup.messages import REBOOT_WARN_MESSAGE
from pleskdistup.upgrader import DistUpgrader, DistUpgraderFactory, PathType


def get_version() -> str:
    with pkg_resources.resource_stream(__name__, "version.json") as f:
        return json.load(f)["version"]


def get_revision(short: bool = True) -> str:
    with pkg_resources.resource_stream(__name__, "version.json") as f:
        revision = json.load(f)["revision"]
        if short:
            revision = revision[:8]
        return revision


class Centos2AlmaConverter(DistUpgrader):
    _distro_from = dist.CentOs("7")
    _distro_to = dist.AlmaLinux("8")

    _pre_reboot_delay = 45

    def __init__(self):
        super().__init__()

        self.upgrade_postgres_allowed = False
        self.remove_unknown_perl_modules = False
        self.disable_spamassasin_plugins = False
        self.amavis_upgrade_allowed = False
        self.allow_raid_devices = False
        self.remove_leapp_logs = False
        self.allow_old_script_version = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(From {self._distro_from}, To {self._distro_to})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"

    @classmethod
    def supports(
        cls,
        from_system: typing.Optional[dist.Distro] = None,
        to_system: typing.Optional[dist.Distro] = None
    ) -> bool:
        return (
            (from_system is None or cls._distro_from == from_system)
            and (to_system is None or cls._distro_to == to_system)
        )

    @property
    def upgrader_name(self) -> str:
        return "Plesk::Centos2AlmaConverter"

    @property
    def upgrader_version(self) -> str:
        return get_version() + "-" + get_revision()

    @property
    def issues_url(self) -> str:
        return "https://github.com/plesk/centos2alma/issues"

    def prepare_feedback(
        self,
        feed: feedback.Feedback,
    ) -> feedback.Feedback:

        feed.collect_actions += [
            feedback.collect_installed_packages_yum,
            feedback.collect_plesk_version,
            feedback.collect_kernel_modules,
        ]

        feed.attached_files += [
            "/etc/fstab",
            "/etc/grub2.cfg",
            "/etc/leapp/files/repomap.csv",
            "/etc/leapp/files/pes-events.json",
            "/etc/leapp/files/leapp_upgrade_repositories.repo",
            "/etc/named.conf",
            "/var/named/chroot/etc/named.conf",
            "/var/named/chroot/etc/named-user-options.conf",
            "/var/log/leapp/leapp-report.txt",
            "/var/log/leapp/leapp-preupgrade.log",
            "/var/log/leapp/leapp-upgrade.log",
        ]

        for grub_directory in ("/etc/grub.d", "/boot/grub", "/boot/grub2"):
            feed.attached_files += files.find_files_case_insensitive(grub_directory, ["*"])

        for repofile in files.find_files_case_insensitive("/etc/yum.repos.d", ["*.repo*"]):
            feed.attached_files.append(repofile)

        for gpgfile in files.find_files_case_insensitive("/etc/leapp/files/vendors.d/rpm-gpg", ["*"]):
            feed.attached_files.append(gpgfile)

        for gpgfile in files.find_files_case_insensitive("/etc/leapp/repos.d/system_upgrade/common/files/rpm-gpg", ["*"], recursive=True):
            feed.attached_files.append(gpgfile)

        return feed

    def construct_actions(
        self,
        upgrader_bin_path: PathType,
        options: typing.Any,
        phase: Phase
    ) -> typing.Dict[str, typing.List[action.ActiveAction]]:
        new_os = str(self._distro_to)

        actions_map = {
            "Status informing": [
                common_actions.HandleConversionStatus(options.status_flag_path, options.completion_flag_path),
                common_actions.AddFinishSshLoginMessage(new_os),  # Executed at the finish phase only
                common_actions.AddInProgressSshLoginMessage(new_os),
            ],
            "Leapp installation": [
                centos2alma_actions.LeapInstallation(remove_logs_on_finish=self.remove_leapp_logs),
            ],
            "Prepare configurations": [
                common_actions.RevertChangesInGrub(),
                centos2alma_actions.PrepareLeappConfigurationBackup(),
                centos2alma_actions.RemoveOldMigratorThirparty(),
                centos2alma_actions.FetchKernelCareGPGKey(),
                centos2alma_actions.FetchPleskGPGKey(),
                centos2alma_actions.FetchImunifyGPGKey(),
                centos2alma_actions.LeapReposConfiguration(),
                centos2alma_actions.LeapChoicesConfiguration(),
                centos2alma_actions.FixEpelPythonPackageMappings(),
                centos2alma_actions.AdoptKolabRepositories(),
                centos2alma_actions.AdoptAtomicRepositories(),
                centos2alma_actions.FixupImunify(),
                common_actions.AddUpgradeSystemdService(os.path.abspath(sys.argv[0]), options),
                common_actions.UpdatePlesk(),
                centos2alma_actions.PostgresReinstallModernPackage(),
                centos2alma_actions.FixNamedConfig(),
                common_actions.DisablePleskSshBanner(),
                centos2alma_actions.FixSyslogLogrotateConfig(options.state_dir),
                common_actions.SetMinDovecotDhParamSize(dhparam_size=2048),
                common_actions.RestoreDovecotConfiguration(options.state_dir),
                common_actions.RestoreRoundcubeConfiguration(options.state_dir),
                centos2alma_actions.RecreateAwstatConfigurationFiles(),
                common_actions.UninstallTuxcareEls(),
                common_actions.PreserveMariadbConfig(),
                common_actions.SubstituteSshPermitRootLoginConfigured(),
            ],
            "Handle plesk related services": [
                common_actions.DisablePleskRelatedServicesDuringUpgrade(),
                common_actions.DisableServiceDuringUpgrade("mailman.service"),
                common_actions.HandlePleskFirewallService(),
            ],
            "Handle packages and services": [
                centos2alma_actions.FixOsVendorPhpFpmConfiguration(),
                common_actions.RebundleRubyApplications(),
                centos2alma_actions.ReinstallPhpmyadminPleskComponents(),
                centos2alma_actions.ReinstallRoundcubePleskComponents(),
                centos2alma_actions.ReinstallConflictPackages(options.state_dir),
                centos2alma_actions.ReinstallPerlCpanModules(options.state_dir),
                centos2alma_actions.DisableSuspiciousKernelModules(),
                common_actions.HandleUpdatedSpamassassinConfig(),
                common_actions.DisableSelinuxDuringUpgrade(),
                centos2alma_actions.RestoreMissingNginx(),
                common_actions.ReinstallAmavisAntivirus(),
                centos2alma_actions.HandleInternetxRepository(),
            ],
            "First plesk start": [
                common_actions.StartPleskBasicServices(),
            ],
            "Remove conflicting packages": [
                centos2alma_actions.RemovingPleskConflictPackages(),
            ],
            "Update databases": [
                centos2alma_actions.UpdateMariadbDatabase(),
                centos2alma_actions.UpdateModernMariadb(),
                centos2alma_actions.AddMysqlConnector(),
            ],
            "Do convert": [
                centos2alma_actions.AdoptRepositories(),
                centos2alma_actions.DoCentos2AlmaConvert(leapp_ovl_size=self.leapp_ovl_size),
            ],
            # This stage includes actions that need to be completed before the adopt repositories
            # on the final stage. This is necessary because AdoptRepositories performs a `dnf update`,
            #  which will fail if there are any unmanaged repositories.
            "Specific repositories adoption": [
                centos2alma_actions.AdoptRackspaceEpelRepository(),
            ],
            "Resume": [
                common_actions.RestoreInProgressSshLoginMessage(new_os),
            ],
            "Pause before reboot": [
            ],
            "Reboot": {
                common_actions.Reboot(
                    prepare_next_phase=Phase.FINISH,
                    post_reboot=action.RebootType.AFTER_LAST_STAGE,
                    name="reboot and perform finishing actions",
                )
            }
        }

        if not options.no_reboot:
            actions_map = util.merge_dicts_of_lists(actions_map, {
                "Pause before reboot": [
                    common_actions.PreRebootPause(
                        REBOOT_WARN_MESSAGE.format(delay=self._pre_reboot_delay, util_name="centos2alma"),
                        self._pre_reboot_delay
                    ),
                ]
            })

        if self.upgrade_postgres_allowed:
            actions_map = util.merge_dicts_of_lists(actions_map, {
                "Prepare configurations": [
                    centos2alma_actions.PostgresDatabasesUpdate(),
                ]
            })

        return actions_map

    def get_check_actions(self, options: typing.Any, phase: Phase) -> typing.List[action.CheckAction]:
        if phase is Phase.FINISH:
            return [centos2alma_actions.AssertDistroIsAlmalinux8()]

        FIRST_SUPPORTED_BY_ALMA_8_PHP_VERSION = "5.6"
        ALMALINUX8_AMAVIS_REQUIRED_RAM = 1.5 * 1024 * 1024 * 1024
        checks = [
            common_actions.AssertPleskVersionIsAvailable(),
            common_actions.AssertPleskInstallerNotInProgress(),
            centos2alma_actions.AssertAvailableSpaceForLocation("/var/lib", 5 * 1024 * 1024 * 1024),  # 5GB required minimum space to store packages
            centos2alma_actions.AssertAvailableSpaceForLocation("/boot", 100 * 1024 * 1024),  # 100M required minimum space to store bootloader
            common_actions.AssertMinPhpVersionInstalled(FIRST_SUPPORTED_BY_ALMA_8_PHP_VERSION),
            common_actions.AssertMinPhpVersionUsedByWebsites(FIRST_SUPPORTED_BY_ALMA_8_PHP_VERSION),
            common_actions.AssertMinPhpVersionUsedByCron(FIRST_SUPPORTED_BY_ALMA_8_PHP_VERSION),
            common_actions.AssertOsVendorPhpUsedByWebsites(FIRST_SUPPORTED_BY_ALMA_8_PHP_VERSION),
            common_actions.AssertGrub2Installed(),
            centos2alma_actions.AssertNoMoreThenOneKernelNamedNIC(),
            centos2alma_actions.AssertRedHatKernelInstalled(),
            centos2alma_actions.AssertLastInstalledKernelInUse(),
            centos2alma_actions.AssertLocalRepositoryNotPresent(),
            centos2alma_actions.AssertIPRepositoryNotPresent(),
            centos2alma_actions.AssertCentosEOLedRepositoriesNotPresent(),
            centos2alma_actions.AssertThereIsNoRepositoryDuplicates(),
            centos2alma_actions.AssertMariadbRepoAvailable(),
            common_actions.AssertNotInContainer(),
            centos2alma_actions.AssertPackagesUpToDate(),
            centos2alma_actions.CheckOutdatedLetsencryptExtensionRepository(),
            centos2alma_actions.AssertPleskRepositoriesNotNoneLink(),
            centos2alma_actions.AssertNoAbsoluteLinksInRoot(),
            centos2alma_actions.CheckSourcePointsToArchiveURL(),
            common_actions.AssertNoMoreThenOneKernelDevelInstalled(),
            common_actions.AssertEnoughRamForAmavis(ALMALINUX8_AMAVIS_REQUIRED_RAM, self.amavis_upgrade_allowed),
            common_actions.AssertSshPermitRootLoginConfigured(skip_known_substitudes=True),
            common_actions.AssertFstabOrderingIsFine(),
            common_actions.AssertFstabHasDirectRaidDevices(self.allow_raid_devices),
            centos2alma_actions.AssertCentosSignedKernelInstalled(),
            common_actions.AssertPackageAvailable(
                "dnf",
                name="asserting dnf package available",
                recommendation="""The dnf package is required for Leapp to function properly.
\tHint: You can install it using the CentOS vault extras repository with the following base URL:
\t\t'baseurl=http://vault.centos.org/centos/$releasever/extras/$basearch/'"""
            ),
            # LiteSpeed is not supported yet
            common_actions.AssertPleskExtensions(not_installed=["litespeed"])
        ]

        if not self.upgrade_postgres_allowed:
            checks.append(centos2alma_actions.AssertOutdatedPostgresNotInstalled())
        else:
            checks.append(centos2alma_actions.AssertPostgresLocaleMatchesSystemOne())
        if not self.remove_unknown_perl_modules:
            checks.append(centos2alma_actions.AssertThereIsNoUnknownPerlCpanModules())
        if not self.disable_spamassasin_plugins:
            checks.append(common_actions.AssertSpamassassinAdditionalPluginsDisabled())

        if not self.allow_old_script_version:
            checks.append(common_actions.AssertScriptVersionUpToDate("https://github.com/plesk/centos2alma", "centos2alma", version.DistupgradeToolVersion(get_version())))

        return checks

    def parse_args(self, args: typing.Sequence[str]) -> None:
        DESC_MESSAGE = f"""Use this script to convert {str(self._distro_from)} server with Plesk to {str(self._distro_to)}. The process consists of the following general stages:

- Preparation (about 20 minutes) - The Leapp utility is installed and configured. The OS is prepared for the conversion. The Leapp utility is then called to create a temporary OS distribution.
- Conversion (about 20 minutes)  - The conversion takes place. During this stage, you cannot connect to the server via SSH.
- Finalization (about 5 minutes) - The server is returned to normal operation.

To see the detailed plan, run the utility with the --show-plan option.

The script writes a log to the /var/log/plesk/centos2alma.log file. If there are any issues, you can find more information in the log file.
For assistance, submit an issue here {self.issues_url} and attach the feedback archive generated with --prepare-feedback or at least the log file..
"""
        parser = argparse.ArgumentParser(
            usage=argparse.SUPPRESS,
            description=DESC_MESSAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False,
        )
        parser.add_argument(
            "-h", "--help", action="help", default=argparse.SUPPRESS,
            help=argparse.SUPPRESS,
        )
        parser.add_argument("--upgrade-postgres", action="store_true", dest="upgrade_postgres_allowed", default=False,
                            help="Upgrade all hosted PostgreSQL databases. To avoid data loss, create backups of all "
                                 "hosted PostgreSQL databases before calling this option.")
        parser.add_argument("--remove-unknown-perl-modules", action="store_true", dest="remove_unknown_perl_modules", default=False,
                            help="Allow to remove unknown perl modules installed from cpan. In this case all modules installed "
                                 "by cpan will be removed. Note that it could lead to some issues with perl scripts")
        parser.add_argument("--disable-spamassasin-plugins", action="store_true", dest="disable_spamassasin_plugins", default=False,
                            help="Disable additional plugins in spamassasin configuration during the conversion.")
        parser.add_argument("--leapp-ovl-size", type=int, dest="leapp_ovl_size", default=4096,
                            help="Specify the overlay size for leapp in megabytes.")
        parser.add_argument("--amavis-upgrade-allowed", action="store_true", dest="amavis_upgrade_allowed", default=False,
                            help="Allow to upgrade amavis antivirus even if there is not enough RAM available.")
        parser.add_argument("--allow-raid-devices", action="store_true", dest="allow_raid_devices", default=False,
                            help="Allow to have direct RAID devices in /etc/fstab. This could lead to unbootable system after the conversion so use the option on your own risk.")
        parser.add_argument("--remove-leapp-logs", action="store_true", dest="remove_leapp_logs", default=False,
                            help="Remove leapp logs after the conversion. By default, the logs are removed after the conversion.")
        parser.add_argument("--allow-old-script-version", action="store_true", dest="allow_old_script_version", default=False,
                            help="Allow to run the script with an old version. By default, the script checks for a new version on GitHub and does not allow to run with an old one.")
        options = parser.parse_args(args)

        self.upgrade_postgres_allowed = options.upgrade_postgres_allowed
        self.remove_unknown_perl_modules = options.remove_unknown_perl_modules
        self.disable_spamassasin_plugins = options.disable_spamassasin_plugins
        self.amavis_upgrade_allowed = options.amavis_upgrade_allowed
        self.leapp_ovl_size = options.leapp_ovl_size
        self.allow_raid_devices = options.allow_raid_devices
        self.remove_leapp_logs = options.remove_leapp_logs
        self.allow_old_script_version = options.allow_old_script_version


class Centos2AlmaConverterFactory(DistUpgraderFactory):
    def __init__(self):
        super().__init__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(upgrader_name={self.upgrader_name})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} (creates {self.upgrader_name})"

    def supports(
        self,
        from_system: typing.Optional[dist.Distro] = None,
        to_system: typing.Optional[dist.Distro] = None
    ) -> bool:
        return Centos2AlmaConverter.supports(from_system, to_system)

    @property
    def upgrader_name(self) -> str:
        return "Plesk::Centos2AlmaConverter"

    def create_upgrader(self, *args, **kwargs) -> DistUpgrader:
        return Centos2AlmaConverter(*args, **kwargs)
