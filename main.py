#!/usr/bin/python3

import actions
import common

import sys
import os
from optparse import OptionParser
from enum import Enum


def merge_dicts_of_lists(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1:
            for item in value:
                dict1[key].append(item)
        else:
            dict1[key] = value
    return dict1


class Stages(str, Enum):
    prepare = 'prepare'
    convert = 'start'
    finish = 'finish'
    # Todo. The tst stage for debugging purpose only, don't forget to remove it
    test = 'test'


def is_required_conditions_satisfied(options):
    if options.stage == Stages.finish:
        return True

    checks = []
    if not options.upgrade_postgres_allowed:
        checks.append(actions.CheckOutdatedPostgresInstalled())

    try:
        with actions.CheckFlow(checks) as check_flow:
            check_flow.validate_actions()
            return check_flow.make_checks()
    except Exception as ex:
        common.log.err("{}".format(ex))
        return False



def construct_actions(options):
    actions_map = {}

    if options.stage == Stages.test:
        raise Exception("There are no steps in the test stage. You could use this stage to call some actions in development porpuses.")

    if not options.stage or options.stage == Stages.prepare or options.stage == Stages.finish:
        actions_map = merge_dicts_of_lists(actions_map, {
            1: [
                actions.LeapInstallation(),
            ],
            2: [
                actions.AddUpgradeSystemdService(os.path.abspath(sys.argv[0])),
                actions.LeapReposConfiguration(),
                actions.AvoidMariadbDowngrade(),
                actions.LeapChoicesConfiguration(),
                actions.FixNamedConfig(),
            ],
        })

    if not options.stage or options.stage == Stages.convert or options.stage == Stages.finish:
        actions_map = merge_dicts_of_lists(actions_map, {
            3: [
                actions.RemovingPackages(),
                actions.PostgresDatabasesUpdate(),
                actions.UpdateMariadbDatabase(),
                actions.ReinstallPleskComponents(),
                actions.DisableSuspiciousKernelModules(),
                actions.RulePleskRelatedServices(),
                actions.RuleSelinux(),
            ],
            4: [
                actions.DoConvert(),
            ],
        })
    if options.stage == Stages.finish:
        actions_map = merge_dicts_of_lists(actions_map, {
            1: [
                actions.FinishMessage(),
            ],
            4: [
                actions.AdoptPleskRepositories(),
                actions.StartPleskBasicServices(),
            ],
        })

    # Autoreboot as an action?

    if options.upgrade_postgres_allowed:
        actions_map = merge_dicts_of_lists(actions_map, {
            3: [
                actions.PostgresDatabasesUpdate(),
            ]
        })

    return actions_map


def main():
    common.log.init_logger(["/var/log/plesk/distupgrader.log"], [sys.stdout], console=True)

    opts = OptionParser(usage="distupgrader [options] [stage]")
    opts.add_option("-s", "--stage", type="choice",
                    choices=(Stages.prepare, Stages.convert, Stages.finish),
                    help="Choose a stage of a conversation process. Prepare should be used before any other actions."
                         "Start - when you ready for a conversation process. The process will take about 20 minutes."
                         "Finish should be called at the end of conversation, right after the first reboot.")
    opts.add_option("--upgrade-postgres", action="store_true", dest="upgrade_postgres_allowed", default=False,
                    help="Allow postgresql database upgrade. Not the operation could be dangerous and wipe your database."
                         "So make sure you backup your database before the upgrade.")

    options, _ = opts.parse_args(args=sys.argv[1:])

    if not is_required_conditions_satisfied(options):
        common.log.err("Please fix noted problems before proceed the conversation")
        return 1

    actions_map = construct_actions(options)

    try:
        with actions.PrepareActionsFlow(actions_map) if options.stage != Stages.finish else actions.FinishActionsFlow(actions_map) as flow:
            flow.validate_actions()
            flow.pass_actions()
    except Exception as ex:
        common.log.err("{}".format(ex))
        return 1

    return 0


if __name__ == "__main__":
    main()
