#!/usr/bin/python3
# Copyright 1999-2024. WebPros International GmbH. All rights reserved.

import actions

from datetime import datetime
import json
import logging
import os
import pkg_resources
import sys
import subprocess
import threading
import typing
import time

from enum import Flag, auto
from optparse import OptionParser, OptionValueError, SUPPRESS_HELP

import messages
from common import action, dist, feedback, files, log, motd, plesk, systemd, writers


DEFAULT_LOG_FILE = "/var/log/plesk/centos2alma.log"
PRE_REBOOT_DELAY = 45
PHP_MINIMAL_VERSION_ON_ALMALINUX = "7.1"


def get_version() -> str:
    with pkg_resources.resource_stream(__name__, "version.json") as f:
        return json.load(f)["version"]


def get_revision(short: bool = True) -> str:
    with pkg_resources.resource_stream(__name__, "version.json") as f:
        revision = json.load(f)["revision"]
        if short:
            revision = revision[:8]
        return revision


def merge_dicts_of_lists(dict1: typing.Dict[typing.Any, typing.Any],
                         dict2: typing.Dict[typing.Any, typing.Any]) -> typing.Dict[typing.Any, typing.Any]:
    for key, value in dict2.items():
        if key in dict1:
            for item in value:
                dict1[key].append(item)
        else:
            dict1[key] = value
    return dict1


def prepare_feedback() -> None:
    feedback_archive: str = "centos2alma_feedback.zip"

    def get_installed_packages_list():
        packages_file = "installed_packages.txt"
        with open(packages_file, "w") as pkgs_file:
            try:
                pkgs_info = subprocess.check_output(["/usr/bin/yum", "list", "installed"], universal_newlines=True).splitlines()
                for line in pkgs_info:
                    pkgs_file.write(line + "\n")
            except subprocess.CalledProcessError:
                pkgs_file.write("Getting installed packages from yum failed\n")

        return packages_file

    def get_plesk_version():
        plesk_version_file = "plesk_version.txt"
        with open(plesk_version_file, "w") as version_file:
            for lines in plesk.get_plesk_full_version():
                version_file.write(lines + "\n")

        return plesk_version_file

    keep_files = [
        DEFAULT_LOG_FILE,
        action.ActiveFlow.PATH_TO_ACTIONS_DATA,
        "/etc/leapp/files/repomap.csv",
        "/etc/leapp/files/pes-events.json",
        "/etc/leapp/files/leapp_upgrade_repositories.repo",
        "/var/log/leapp/leapp-report.txt",
        "/var/log/leapp/leapp-preupgrade.log",
        "/var/log/leapp/leapp-upgrade.log",
    ]

    for repofile in files.find_files_case_insensitive("/etc/yum.repos.d", ["*.repo*"]):
        keep_files.append(repofile)

    prepare_feedback = feedback.Feedback("centos2alma", get_version() + "-" + get_revision(), keep_files,
                                         [
                                            get_installed_packages_list,
                                            get_plesk_version,
                                         ])
    prepare_feedback.save_archive(feedback_archive)

    print(messages.FEEDBACK_IS_READY_MESSAGE.format(feedback_archive_path=feedback_archive))


class Stages(Flag):
    convert = auto()
    finish = auto()
    revert = auto()
    # Todo. The tst stage for debugging purpose only, don't forget to remove it
    test = auto()


def convert_string_to_stage(option, opt_str, value, parser):
    if value == "start" or value == "convert":
        parser.values.stage = Stages.convert
        return
    elif value == "finish":
        parser.values.stage = Stages.finish
        return
    elif value == "revert":
        parser.values.stage = Stages.revert
        return
    elif value == "test":
        parser.values.stage = Stages.test
        return

    raise OptionValueError("Unknown stage: {}".format(value))


def is_required_conditions_satisfied(options: typing.Any, stage_flag: Stages) -> bool:
    checks = []
    if Stages.finish in stage_flag:
        checks = [
            actions.DistroIsAlmalinux8(),
        ]
    else:
        checks = [
            actions.DistroIsCentos79(),
            actions.PleskVersionIsActual(),
            actions.PleskInstallerNotInProgress(),
            actions.CheckAvailableSpace(),
            actions.AssertMinPhpVersionInstalled(PHP_MINIMAL_VERSION_ON_ALMALINUX),
            actions.AssertMinPhpVersionUsedByWebsites(PHP_MINIMAL_VERSION_ON_ALMALINUX),
            actions.AssertMinPhpVersionUsedByCron(PHP_MINIMAL_VERSION_ON_ALMALINUX),
            actions.AssertOSVendorPHPUsedByWebsites(PHP_MINIMAL_VERSION_ON_ALMALINUX),
            actions.CheckGrubInstalled(),
            actions.CheckNoMoreThenOneKernelNamedNIC(),
            actions.CheckIsInContainer(),
            actions.CheckLastInstalledKernelInUse(),
            actions.CheckIsLocalRepositoryNotPresent(),
            actions.CheckRepositoryDuplicates(),
            actions.CheckMariadbRepoAvailable(),
            actions.CheckPackagesUpToDate(),
            actions.CheckOutdatedLetsencryptExtensionRepository(),
        ]
        if not options.upgrade_postgres_allowed:
            checks.append(actions.CheckOutdatedPostgresInstalled())
        if not options.remove_unknown_perl_modules:
            checks.append(actions.CheckUnknownPerlCpanModules())
        if not options.disable_spamassasin_plugins:
            checks.append(actions.CheckSpamassassinPlugins())

    try:
        with action.CheckFlow(checks) as check_flow, writers.StdoutWriter() as writer:
            writer.write("Do preparation checks...")
            check_flow.validate_actions()
            failed_checks = check_flow.make_checks()
            writer.write("\r")
            for check in failed_checks:
                writer.write(check)
                log.err(check)

            if failed_checks:
                return False
            return True
    except Exception as ex:
        log.err("{}".format(ex))
        return False


def construct_actions(options: typing.Any, stage_flag: Stages) -> typing.Dict[int, typing.List[action.ActiveAction]]:
    actions_map = {}

    if Stages.test in stage_flag:
        raise Exception("There are no steps in the test stage. You could use this stage to call some actions in development purposes.")

    actions_map = merge_dicts_of_lists(actions_map, {
        1: [
            actions.HandleConversionStatus(),
            actions.LeapInstallation(),
            actions.AddInProgressSshLoginMessage(),
            actions.RevertChangesInGrub(),
        ],
        2: [
            actions.PrepareLeappConfigurationBackup(),
            actions.RemoveOldMigratorThirparty(),
            actions.LeapReposConfiguration(),
            actions.LeapChoicesConfiguration(),
            actions.AdoptKolabRepositories(),
            actions.FixupImunify(),
            actions.PatchLeappErrorOutput(),
            actions.PatchLeappDebugNonAsciiPackager(),
            actions.AddUpgradeSystemdService(os.path.abspath(sys.argv[0]), options),
            actions.UpdatePlesk(),
            actions.PostgresReinstallModernPackage(),
            actions.FixNamedConfig(),
            actions.RecreateAwstatConfigurationFiles(),
            actions.IncreaseDovecotDHParameters(),
            actions.FixOsVendorPhpFpmConfiguration(),
        ],
        3: [
            actions.DisablePleskSshBanner(),
            actions.RemovingPleskConflictPackages(),
            actions.ReinstallPleskComponents(),
            actions.ReinstallConflictPackages(),
            actions.ReinstallPerlCpanModules(),
            actions.DisableSuspiciousKernelModules(),
            actions.FixSpamassassinConfig(),
            actions.RulePleskRelatedServices(),
            actions.RuleSelinux(),
            actions.RestoreMissingNginx(),
        ],
        4: [
            actions.StartPleskBasicServices(),
        ],
        5: [
            actions.UpdateMariadbDatabase(),
            actions.UpdateModernMariadb(),
            actions.AddMysqlConnector(),
        ],
        6: [
            actions.DoConvert(),
        ],
        7: [
            actions.PreRebootPause(messages.REBOOT_WARN_MESSAGE.format(delay=PRE_REBOOT_DELAY), PRE_REBOOT_DELAY),
        ]
    })

    if options.upgrade_postgres_allowed:
        actions_map = merge_dicts_of_lists(actions_map, {
            3: [
                actions.PostgresDatabasesUpdate(),
            ]
        })

    if Stages.finish in stage_flag:
        actions_map = merge_dicts_of_lists(actions_map, {
            1: [
                actions.AddFinishSshLoginMessage(),
            ],
            2: [
                actions.RebundleRubyApplications(),
                actions.FixSyslogLogrotateConfig(),
            ],
            6: [
                actions.AdoptRepositories(),
            ]
        })

    return actions_map


def get_flow(stage_flag: Stages, actions_map: typing.Dict[int, typing.List[action.ActiveAction]]) -> action.ActiveFlow:
    if Stages.finish in stage_flag:
        return action.FinishActionsFlow(actions_map)
    elif Stages.revert in stage_flag:
        return action.RevertActionsFlow(actions_map)
    else:
        return action.PrepareActionsFlow(actions_map)


def start_flow(flow: action.ActiveFlow) -> None:
    with writers.FileWriter(STATUS_FILE_PATH) as status_writer, writers.StdoutWriter() as stdout_writer:
        progressbar = action.FlowProgressbar(flow, [stdout_writer, status_writer],
                                             messages.TIME_EXCEEDED_MESSAGE.format(DEFAULT_LOG_FILE))
        progress = threading.Thread(target=progressbar.display)
        executor = threading.Thread(target=flow.pass_actions)

        progress.start()
        executor.start()

        executor.join()
        progress.join()


STATUS_FILE_PATH = "/tmp/centos2alma.status"


def show_status() -> None:
    if not os.path.exists(STATUS_FILE_PATH):
        print("Conversion process is not running.")
        return

    print("Conversion process in progress:")
    status = files.get_last_lines(STATUS_FILE_PATH, 1)
    print(status[0])


def monitor_status() -> None:
    if not os.path.exists(STATUS_FILE_PATH):
        print("Conversion process is not running.")
        return

    with open(STATUS_FILE_PATH, "r") as status:
        status.readlines()
        while os.path.exists(STATUS_FILE_PATH):
            line = status.readline().rstrip()
            sys.stdout.write("\r" + line)
            sys.stdout.flush()
            time.sleep(1)


def show_fail_motd() -> None:
    motd.add_finish_ssh_login_message("""
Something went wrong during the final stage of CentOS 7 to AlmaLinux 8 conversion
See the /var/log/plesk/centos2alma.log file for more information.
""")
    motd.publish_finish_ssh_login_message()


def handle_error(error: str) -> None:
    sys.stdout.write("\n{}\n".format(error))
    sys.stdout.write(messages.FAIL_MESSAGE_HEAD.format(DEFAULT_LOG_FILE))

    error_message = f"centos2alma (version {get_version()}-{get_revision()}) process has been failed. Error: {error}.\n\n"
    for line in files.get_last_lines(DEFAULT_LOG_FILE, 100):
        sys.stdout.write(line)
        error_message += line

    sys.stdout.write(messages.FAIL_MESSAGE_TAIL.format(DEFAULT_LOG_FILE))

    plesk.send_error_report(error_message)
    plesk.send_conversion_status(False)

    log.err(f"centos2alma process has been failed. Error: {error}")
    show_fail_motd()


def do_convert(options: typing.Any) -> None:
    if not is_required_conditions_satisfied(options, options.stage):
        log.err("Please fix noted problems before proceed the conversion")
        return 1

    actions_map = construct_actions(options, options.stage)

    with get_flow(options.stage, actions_map) as flow:
        flow.validate_actions()
        start_flow(flow)
        if flow.is_failed():
            handle_error(flow.get_error())
            return 1

    if not options.no_reboot and (Stages.convert in options.stage or Stages.finish in options.stage):
        log.info("Going to reboot the system")
        if Stages.convert in options.stage:
            sys.stdout.write(messages.CONVERT_RESTART_MESSAGE.format(time=datetime.now().strftime("%H:%M:%S"),
                                                                     script_path=os.path.abspath(sys.argv[0])))
        elif Stages.finish in options.stage:
            sys.stdout.write(messages.FINISH_RESTART_MESSAGE)

        subprocess.call(["/usr/bin/systemctl", "reboot"])

    if Stages.revert in options.stage:
        sys.stdout.write(messages.REVET_FINISHED_MESSAGE)


HELP_MESSAGE = f"""centos2alma [options]


Use this script to convert a CentOS 7 server with Plesk to AlmaLinux 8. The process consists of three stages:


- Preparation (about 20 minutes) - The Leapp utility is installed and configured. The OS is prepared for the conversion. The Leapp utility is then called to create a temporary OS distribution.
- Conversion (about 20 minutes)  - The conversion takes place. During this stage, you cannot connect to the server via SSH.
- Finalization (about 5 minutes) - The server is returned to normal operation.



The script writes a log to the /var/log/plesk/centos2alma.log file. If there are any issues, you can find more information in the log file.
For assistance, submit an issue here https://github.com/plesk/centos2alma/issues and attach this log file.


centos2alma version is {get_version()}-{get_revision()}.
"""


def main():
    opts = OptionParser(usage=HELP_MESSAGE)
    opts.set_default("stage", Stages.convert)
    opts.add_option("--start", action="store_const", dest="stage", const=Stages.convert,
                    help="Start the conversion stage. This calls the Leapp utility to convert the system "
                         "and reboot into the temporary OS distribution.")
    opts.add_option("-r", "--revert", action="store_const", dest="stage", const=Stages.revert,
                    help="Revert all changes made by the centos2alma. This option can only take effect "
                         "if the server has not yet been rebooted into the temporary OS distribution.")
    opts.add_option("--finish", action="store_const", dest="stage", const=Stages.finish,
                    help="Start the finalization stage. This returns Plesk to normal operation. "
                         "Can be run again if the conversion process failed to finish successfully earlier.")
    opts.add_option("-t", "--test", action="store_const", dest="stage", const=Stages.test, help=SUPPRESS_HELP)
    opts.add_option("--retry", action="store_true", dest="retry", default=False,
                    help="Retry the most recently started stage. This option can only take effect "
                         "during the preparation stage.")
    opts.add_option("--status", action="store_true", dest="status", default=False,
                    help="Show the current status of the conversion process.")
    opts.add_option("--monitor", action="store_true", dest="monitor", default=False,
                    help="Monitor the status of the conversion process in real time.")
    opts.add_option("--upgrade-postgres", action="store_true", dest="upgrade_postgres_allowed", default=False,
                    help="Upgrade all hosted PostgreSQL databases. To avoid data loss, create backups of all "
                         "hosted PostgreSQL databases before calling this option.")
    opts.add_option("--remove-unknown-perl-modules", action="store_true", dest="remove_unknown_perl_modules", default=False,
                    help="Allow to remove unknown perl modules installed from cpan. In this case all modules installed "
                         "by cpan will be removed. Note that it could lead to some issues with perl scripts")
    opts.add_option("--disable-spamassasin-plugins", action="store_true", dest="disable_spamassasin_plugins", default=False,
                    help="Disable additional plugins in spamassasin configuration during the conversion.")
    opts.add_option("-s", "--stage", action="callback", callback=convert_string_to_stage, type="string",
                    help="Start one of the conversion process' stages. Allowed values: 'start', 'revert', and 'finish'.")
    opts.add_option("-v", "--version", action="store_true", dest="version", default=False,
                    help="Show the version of the centos2alma utility.")
    opts.add_option("-f", "--prepare-feedback", action="store_true", dest="prepare_feedback", default=False,
                    help="Prepare feedback archive that should be sent to the developers for further failure investigation.")
    opts.add_option("--verbose", action="store_true", dest="verbose", default=False, help="Write verbose logs")
    opts.add_option("--no-reboot", action="store_true", dest="no_reboot", default=False, help=SUPPRESS_HELP)

    options, _ = opts.parse_args(args=sys.argv[1:])

    log.init_logger([DEFAULT_LOG_FILE], [], loglevel=logging.DEBUG if options.verbose else logging.INFO)

    if not os.path.exists(plesk.CONVERTER_TEMP_DIRECTORY):
        os.mkdir(plesk.CONVERTER_TEMP_DIRECTORY, 0o750)

    if options.version:
        print(get_version() + "-" + get_revision())
        return 0

    if options.prepare_feedback:
        prepare_feedback()
        return 0

    if options.status:
        show_status()
        return 0

    if options.monitor:
        monitor_status()
        return 0

    return do_convert(options)


if __name__ == "__main__":
    main()
