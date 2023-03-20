#!/usr/bin/python3

import actions
import common

from datetime import datetime
import json
import os
import pkg_resources
import sys
import subprocess
import threading
import time

from enum import Flag, auto
from optparse import OptionParser, OptionValueError


def get_version():
    with pkg_resources.resource_stream(__name__, "version.json") as f:
        return json.load(f)["version"]


def get_revision(short=True):
    with pkg_resources.resource_stream(__name__, "version.json") as f:
        revision = json.load(f)["revision"]
        if short:
            revision = revision[:8]
        return revision


def merge_dicts_of_lists(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1:
            for item in value:
                dict1[key].append(item)
        else:
            dict1[key] = value
    return dict1


class Stages(Flag):
    prepare = auto()
    convert = auto()
    finish = auto()
    revert = auto()
    # Todo. The tst stage for debugging purpose only, don't forget to remove it
    test = auto()


def convert_string_to_stage(option, opt_str, value, parser):
    if value == "prepare":
        parser.values.stage = Stages.prepare
        return
    elif value == "start" or value == "convert":
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


def is_required_conditions_satisfied(options, stage_flag):
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
        ]
        if not options.upgrade_postgres_allowed:
            checks.append(actions.CheckOutdatedPostgresInstalled())

    try:
        with actions.CheckFlow(checks) as check_flow:
            check_flow.validate_actions()
            failed_checks = check_flow.make_checks()
            for check in failed_checks:
                sys.stdout.write(check)
                common.log.err(check)

            if failed_checks:
                return False
            return True
    except Exception as ex:
        common.log.err("{}".format(ex))
        return False


def construct_actions(options, stage_flag):
    actions_map = {}

    if Stages.test in stage_flag:
        raise Exception("There are no steps in the test stage. You could use this stage to call some actions in development purposes.")

    if Stages.prepare in stage_flag or Stages.finish in stage_flag or Stages.revert in stage_flag:
        actions_map = merge_dicts_of_lists(actions_map, {
            1: [
                actions.LeapInstallation(),
            ],
            2: [
                actions.LeapReposConfiguration(),
                actions.AvoidMariadbDowngrade(),
                actions.LeapChoicesConfiguration(),
                actions.AdoptKolabRepositories(),
                actions.FixupImunify(),
                actions.PatchLeappErrorOutput(),
            ],
        })

    if Stages.convert in stage_flag or Stages.finish in stage_flag or Stages.revert in stage_flag:
        actions_map = merge_dicts_of_lists(actions_map, {
            2: [
                actions.AddUpgradeSystemdService(os.path.abspath(sys.argv[0])),
                actions.UpdatePlesk(),
                actions.PostgresReinstallModernPackage(),
                actions.FixNamedConfig(),
            ],
            3: [
                actions.RemovingPackages(),
                actions.PostgresDatabasesUpdate(),
                actions.UpdateMariadbDatabase(),
                actions.AddMysqlConnector(),
                actions.ReinstallPleskComponents(),
                actions.DisableSuspiciousKernelModules(),
                actions.FixSpamassassinConfig(),
                actions.RulePleskRelatedServices(),
                actions.RuleSelinux(),
            ],
            4: [
                actions.DoConvert(),
                actions.AddInProgressSshLoginMessage(),
            ],
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
            4: [
                actions.AdoptPleskRepositories(),
                actions.StartPleskBasicServices(),
            ],
        })

    return actions_map


def get_flow(stage_flag, actions_map):
    if Stages.finish in stage_flag:
        return actions.FinishActionsFlow(actions_map)
    elif Stages.revert in stage_flag:
        return actions.RevertActionsFlow(actions_map)
    else:
        return actions.PrepareActionsFlow(actions_map)


def inform_about_problems():
    with open("/etc/motd", "a") as motd:
        motd.write("""
===============================================================================
Message from Plesk centos2alma tool:
Something went wrong during the final stage of CentOS 7 to AlmaLinux 8 conversion
See the /var/log/plesk/centos2alma.log file for more information.
You can remove this message from the /etc/motd file.
===============================================================================
""")


def start_flow(flow):
    with common.FileWriter(STATUS_FILE_PATH) as status_writer, common.StdoutWriter() as stdout_writer:
        progressbar = actions.FlowProgressbar(flow, [stdout_writer, status_writer])
        progress = threading.Thread(target=progressbar.display)
        executor = threading.Thread(target=flow.pass_actions)

        progress.start()
        executor.start()

        executor.join()
        progress.join()


STATUS_FILE_PATH = "/tmp/centos2alma.status"


def show_status():
    if not os.path.exists(STATUS_FILE_PATH):
        print("Conversion process is not running.")
        return

    print("Conversion process in progress:")
    status = common.get_last_lines(STATUS_FILE_PATH, 1)
    print(status[0])


def monitor_status():
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


def handle_error(error):
    sys.stdout.write("\n{}\n".format(error))
    sys.stdout.write(common.FAIL_MESSAGE.format(common.DEFAULT_LOG_FILE))
    sys.stdout.write("Last 100 lines of the log file:\n")

    error_message = f"centos2alma process has been failed. Error: {error}.\n\n"
    for line in common.get_last_lines(common.DEFAULT_LOG_FILE, 100):
        sys.stdout.write(line)
        error_message += line

    # Todo. For now we works only on RHEL-based distros, so the path
    # to the send-error-report utility will be the same.
    # But if we will support Debian-based we should choose path carefully
    send_error_path = "/usr/local/psa/admin/bin/send-error-report"
    try:
        if os.path.exists(send_error_path):
            subprocess.run([send_error_path, "backend"], input=error_message.encode())
    except Exception:
        # We don't care about errors to avoid mislead of the user
        pass

    common.log.err(f"centos2alma process has been failed. Error: {error}")


def do_convert(options):
    if not is_required_conditions_satisfied(options, options.stage):
        common.log.err("Please fix noted problems before proceed the conversation")
        return 1

    actions_map = construct_actions(options, options.stage)

    with get_flow(options.stage, actions_map) as flow:
        flow.validate_actions()
        start_flow(flow)
        if flow.is_failed():
            handle_error(flow.get_error())

            if options.stage == Stages.finish:
                inform_about_problems()

            return 1

    if Stages.convert in options.stage or Stages.finish in options.stage:
        common.log.info("Going to reboot the system")
        if Stages.convert in options.stage:
            sys.stdout.write(common.CONVERT_RESTART_MESSAGE.format(time=datetime.now().strftime("%H:%M:%S"),
                                                                   script_path=os.path.abspath(sys.argv[0])))
        elif Stages.finish in options.stage:
            sys.stdout.write(common.FINISH_RESTART_MESSAGE)

        subprocess.call(["systemctl", "reboot"])

    if Stages.revert in options.stage:
        sys.stdout.write(common.REVET_FINISHED_MESSAGE)


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
    common.log.init_logger([common.DEFAULT_LOG_FILE], [])

    opts = OptionParser(usage=HELP_MESSAGE)
    opts.set_default("stage", Stages.prepare | Stages.convert)
    opts.add_option("--prepare", action="store_const", dest="stage", const=Stages.prepare,
                    help="Start the preparation stage. This installs and configures the Leapp utility. "
                         "This option does not interfere with normal Plesk operation, "
                         "and can be called safely before any other actions.")
    opts.add_option("--start", action="store_const", dest="stage", const=Stages.convert,
                    help="Start the conversion stage. This calls the Leapp utility to convert the system "
                         "and reboot into the temporary OS distribution.")
    opts.add_option("-r", "--revert", action="store_const", dest="stage", const=Stages.revert,
                    help="Revert all changes made by the centos2alma. This option can only take effect "
                         "if the server has not yet been rebooted into the temporary OS distribution.")
    opts.add_option("--finish", action="store_const", dest="stage", const=Stages.finish,
                    help="Start the finalization stage. This returns Plesk to normal operation. "
                         "Can be run again if the conversion process failed to finish successfully earlier.")
    opts.add_option("--retry", action="store_true", dest="retry", default=False,
                    help="Retry the most recently started stage. This option can only take effect "
                         "during the 'prepare' or 'start' stages.")
    opts.add_option("--status", action="store_true", dest="status", default=False,
                    help="Show the current status of the conversion process.")
    opts.add_option("--monitor", action="store_true", dest="monitor", default=False,
                    help="Monitor the status of the conversion process in real time.")
    opts.add_option("--upgrade-postgres", action="store_true", dest="upgrade_postgres_allowed", default=False,
                    help="Upgrade all hosted PostgreSQL databases. To avoid data loss, create backups of all "
                         "hosted PostgreSQL databases before calling this option.")
    opts.add_option("-s", "--stage", action="callback", callback=convert_string_to_stage, type="string",
                    help="Start one of the conversion process' stages. Allowed values: 'prepare', 'start', 'revert', and 'finish'.")
    opts.add_option("-v", "--version", action="store_true", dest="version", default=False,
                    help="Show the version of the centos2alma utility.")

    options, _ = opts.parse_args(args=sys.argv[1:])

    if options.version:
        print(get_version() + "-" + get_revision())
        return 0

    if options.status:
        show_status()
        return 0
    
    if options.monitor:
        monitor_status()
        return 0

    do_convert(options)
    return 0


if __name__ == "__main__":
    main()
