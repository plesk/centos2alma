#!/usr/bin/python3

import actions
import common

from datetime import datetime
import os
import sys
import subprocess
import threading
import time

from enum import Flag, auto
from optparse import OptionParser, OptionValueError


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
            actions.DistroIsCentos7(),
            actions.PleskInstallerNotInProgress(),
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
                actions.AddUpgradeSystemdService(os.path.abspath(sys.argv[0])),
                actions.LeapReposConfiguration(),
                actions.AvoidMariadbDowngrade(),
                actions.PostgresReinstallModernPackage(),
                actions.LeapChoicesConfiguration(),
                actions.FixupImunify(),
                actions.PatchLeappErrorOutput(),
                actions.FixNamedConfig(),
            ],
        })

    if Stages.convert in stage_flag or Stages.finish in stage_flag or Stages.revert in stage_flag:
        actions_map = merge_dicts_of_lists(actions_map, {
            2: [
                actions.UpdatePlesk(),
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
Message from Plesk distupgrade tool:
Something is wrong during finishing stage of Centos 7 to AlmaLinux 8 conversion
Please check /var/log/plesk/distupgrader.log for more details.
Please remove this message from /etc/motd file.
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


STATUS_FILE_PATH = "/tmp/distupgrader.status"


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

    error_message = f"Distupgrade process has been failed. Error: {error}.\n\n"
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

    common.log.err(f"Distupgrade process has been failed. Error: {error}")


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


HELP_MESSAGE = f"""distupgrader [options]


This is a script that can be used to convert a CentOS 7 server with Plesk to AlmaLinux 8. The process involves three parts:
- Preparation - In this part, leapp is installed and configured, and the system is prepared for the conversion.
                The leapp utility is then called, which creates a temporary distribution for the conversion.
                This part should take no more than 20 minutes.
- Conversion  - This is the main part of the process, which occurs inside the temporary distribution.
                During this process, it will not be possible to connect to the server via ssh.
                The conversion process should take about 20 minutes.
- Finishing   - This is the last part of the process, which will return the server to its working state.
                The process should take about no more than 5 minutes


The process will write a log to the {common.DEFAULT_LOG_FILE} file. If there are any issues, please check this file for more details.
If you face some problems, please submit an issue to https://github.com/plesk/distupgrader/issues with attached log file.
"""


def main():
    common.log.init_logger([common.DEFAULT_LOG_FILE], [], console=True)

    opts = OptionParser(usage=HELP_MESSAGE)
    opts.set_default("stage", Stages.prepare | Stages.convert)
    opts.add_option("--prepare", action="store_const", dest="stage", const=Stages.prepare,
                    help="Call only prepare stage. This stage installs and configures leapp."
                         "Plesk will still be in a working state after this stage,"
                         "so it is safe to call this stage before any other actions.")
    opts.add_option("--start", action="store_const", dest="stage", const=Stages.convert,
                    help="Call only convert stage. This stage calls the leapp utility to convert the system"
                         "and reboot the instance to enter the temporary distribution.")
    opts.add_option("-r", "--revert", action="store_const", dest="stage", const=Stages.revert,
                    help="Revert all changes made by the distupgrader if moving to AlmaLinux is not performed yet.")
    opts.add_option("--finish", action="store_const", dest="stage", const=Stages.finish,
                    help="Call only finish stage. This stage will be automatically called after the conversion is finished"
                         "and will return Plesk to its working state."
                         "If the previous finish failed, this stage can be called again.")
    opts.add_option("--retry", action="store_true", dest="retry", default=False,
                    help="Option could be used to retry conversion process if it was failed")
    opts.add_option("--status", action="store_true", dest="status", default=False,
                    help="Show status of the conversion process.")
    opts.add_option("--monitor", action="store_true", dest="monitor", default=False,
                    help="Live monitor status of the conversion process.")
    opts.add_option("--upgrade-postgres", action="store_true", dest="upgrade_postgres_allowed", default=False,
                    help="Allow postgresql database upgrade. Not the operation could be dangerous and wipe your database."
                         "So make sure you backup your database before the upgrade.")
    opts.add_option("-s", "--stage", action="callback", callback=convert_string_to_stage, type="string",
                    help="Choose a stage of a conversation process. Available stages: 'prepare', 'start', 'revert', 'finish'.")

    options, _ = opts.parse_args(args=sys.argv[1:])

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
