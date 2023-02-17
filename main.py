#!/usr/bin/python3

import actions
import common

import subprocess
import sys
import os
from optparse import OptionParser
from enum import Enum, Flag, auto


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
                actions.FinishMessage(),
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
        stage_flag = Stages.revert

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


def main():
    common.log.init_logger(["/var/log/plesk/distupgrader.log"], [sys.stdout], console=True)

    opts = OptionParser(usage="distupgrader [options] [stage]")
    opts.add_option("-s", "--stage", type="choice",
                    choices=(StagesStrings.prepare, StagesStrings.convert, StagesStrings.finish, StagesStrings.revert),
                    help="Choose a stage of a conversation process. Prepare should be used before any other actions."
                         "Start - when you ready for a conversation process. The process will take about 20 minutes."
                         "Finish should be called at the end of conversation, right after the first reboot.")
    opts.add_option("-r", "--revert", action="store_true", dest="revert", default=False,
                    help="Revert all changes made by the distupgrader if moving to AlmaLinux is not performed yet.")
    opts.add_option("--upgrade-postgres", action="store_true", dest="upgrade_postgres_allowed", default=False,
                    help="Allow postgresql database upgrade. Not the operation could be dangerous and wipe your database."
                         "So make sure you backup your database before the upgrade.")

    options, _ = opts.parse_args(args=sys.argv[1:])

    stage_flag = extract_stage_flag(options)

    if not is_required_conditions_satisfied(options, stage_flag):
        common.log.err("Please fix noted problems before proceed the conversation")
        return 1

    actions_map = construct_actions(options, stage_flag)

    try:
        with get_flow(stage_flag, actions_map) as flow:
            flow.validate_actions()
            flow.pass_actions()
    except Exception as ex:
        common.log.err("{}".format(ex))
        if stage_flag == Stages.finish:
            inform_about_problems()

        return 1

    if Stages.convert in stage_flag or Stages.finish in stage_flag:
        common.log.info("Going to reboot the system")
        subprocess.call(["systemctl", "reboot"])

    return 0


if __name__ == "__main__":
    main()
