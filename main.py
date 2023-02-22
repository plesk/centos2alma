#!/usr/bin/python3

import actions
import common

from datetime import datetime
import os
import sys
import subprocess
import threading

from enum import Enum, Flag, auto
from optparse import OptionParser


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


class StagesStrings(str, Enum):
    prepare = "prepare"
    convert = "start"
    finish = "finish"
    revert = "revert"
    # Todo. The tst stage for debugging purpose only, don't forget to remove it
    test = "test"


def is_required_conditions_satisfied(options, stage_flag):
    if Stages.finish in stage_flag:
        return True

    checks = [
        actions.PleskInstallerNotInProgress(),
    ]
    if not options.upgrade_postgres_allowed:
        checks.append(actions.CheckOutdatedPostgresInstalled())

    try:
        with actions.CheckFlow(checks) as check_flow:
            check_flow.validate_actions()
            return check_flow.make_checks()
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


def extract_stage_flag(options):
    # revert flag has the highest priority
    if options.revert:
        return Stages.revert

    if options.stage is None:
        return Stages.prepare | Stages.convert
    elif options.stage == StagesStrings.prepare:
        return Stages.prepare
    elif options.stage == StagesStrings.convert:
        return Stages.convert
    elif options.stage == StagesStrings.finish:
        return Stages.finish
    elif options.stage == StagesStrings.revert:
        return Stages.revert
    elif options.stage == StagesStrings.test:
        return Stages.test

    raise Exception("Unknown stage: {}".format(options.stage))


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
    progressbar = actions.FlowProgressbar(flow)
    progress = threading.Thread(target=progressbar.display)
    executor = threading.Thread(target=flow.pass_actions)

    progress.start()
    executor.start()

    executor.join()
    progress.join()


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
We recommend to call for support with this file attached to solve problems with conversion.

The script can be called at different stages of the conversion process. The stages are:
prepare - This stage installs and configures leapp. Plesk will still be in a working state after this stage,
          so it is safe to call this stage before any other actions.
convert - This stage calls the leapp utility to convert the system and reboot the instance to enter the temporary distribution.
revert  - This stage can be called if the convert stage fails and will return Plesk to its working state.
finish  - This stage will be automatically called after the conversion is finished and will return Plesk to its working state.
          If the previous finish failed, this stage can be called again.
"""


def main():
    common.log.init_logger([common.DEFAULT_LOG_FILE], [], console=True)

    opts = OptionParser(usage=HELP_MESSAGE)
    opts.add_option("-s", "--stage", type="choice",
                    choices=(StagesStrings.prepare, StagesStrings.convert, StagesStrings.finish, StagesStrings.revert),
                    help="Choose a stage of a conversation process. Available stages: prepare, start, revert, finish.")
    opts.add_option("-r", "--revert", action="store_true", dest="revert", default=False,
                    help="Revert all changes made by the distupgrader if moving to AlmaLinux is not performed yet.")
    opts.add_option("--retry", action="store_true", dest="retry", default=False,
                    help="Option could be used to retry conversion process if it was failed")
    opts.add_option("--upgrade-postgres", action="store_true", dest="upgrade_postgres_allowed", default=False,
                    help="Allow postgresql database upgrade. Not the operation could be dangerous and wipe your database."
                         "So make sure you backup your database before the upgrade.")

    options, _ = opts.parse_args(args=sys.argv[1:])

    stage_flag = extract_stage_flag(options)

    if not is_required_conditions_satisfied(options, stage_flag):
        common.log.err("Please fix noted problems before proceed the conversation")
        return 1

    actions_map = construct_actions(options, stage_flag)

    with get_flow(stage_flag, actions_map) as flow:
        flow.validate_actions()
        start_flow(flow)
        if flow.is_failed():
            common.log.err("Distupgrade process has been failed. Error: {}".format(flow.get_error()))

            sys.stdout.write("\n{}\n".format(flow.get_error()))
            sys.stdout.write(common.FAIL_MESSAGE.format(common.DEFAULT_LOG_FILE))
            sys.stdout.write("Last 100 lines of the log file:\n")
            for line in common.get_last_lines(common.DEFAULT_LOG_FILE, 100):
                sys.stdout.write(line)

            if stage_flag == Stages.finish:
                inform_about_problems()
            return 1

    if Stages.convert in stage_flag or Stages.finish in stage_flag:
        common.log.info("Going to reboot the system")
        if Stages.convert in stage_flag:
            sys.stdout.write(common.CONVERT_RESTART_MESSAGE.format(datetime.now().strftime("%H:%M:%S")))
        elif Stages.finish in stage_flag:
            sys.stdout.write(common.FINISH_RESTART_MESSAGE)

        subprocess.call(["systemctl", "reboot"])

    if Stages.revert in stage_flag:
        sys.stdout.write(common.REVET_FINISHED_MESSAGE)

    return 0


if __name__ == "__main__":
    main()
