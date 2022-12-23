#!/usr/bin/python3
# Copyright 1999-2022. Plesk International GmbH. All rights reserved.

import actions
import common
# import logging

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


if __name__ == "__main__":
    common.log.init_logger(["/var/log/plesk/distupgrader.log"], [sys.stdout], console=True)

    opts = OptionParser(usage="distupgrader [options] [stage]")
    opts.add_option('-s', '--stage', type='choice',
                    choices=(Stages.prepare, Stages.convert, Stages.finish),
                    help='Choose a stage of a convertation process. Prepare should be used before any other actions.'
                         'Start - when you ready for a convertation process. The process will take about 20 minutes.'
                         'Finish should be called at the end of convertation, right after the first reboot.')
    opts.add_option('--upgrade-postgres', action='store_true', dest='upgrade_postgres_allowed', default=False,
                    help='Allow postgresql database upgrade. Not the operation could be dangerous and wipe your database.'
                         'So make sure you backup your database before the upgrade.')

    options, args = opts.parse_args(args=sys.argv[1:])

    actions_map = {}

    if not options.upgrade_postgres_allowed:
        actions_map = merge_dicts_of_lists(actions_map, {
            1: [
                actions.CheckOutdatedPostgresInstalled(),
            ]
        })
    else:
        actions_map = merge_dicts_of_lists(actions_map, {
            3: [
                actions.PostgresDatabasesUpdate(),
            ]
        })

    if not options.stage or options.stage == Stages.prepare or options.stage == Stages.finish:
        actions_map = merge_dicts_of_lists(actions_map, {
            1: [
                actions.LeapInstallation(),
            ],
            2: [
                actions.AddUpgraderSystemdService(os.path.abspath(sys.argv[0])),
                actions.LeapReposConfiguration(),
                actions.LeapChoisesConfiguration(),
                actions.FixNamedConfig(),
            ],
        })

    if not options.stage or options.stage == Stages.convert or options.stage == Stages.finish:
        actions_map = merge_dicts_of_lists(actions_map, {
            3: [
                actions.RemovingPackages(),
                actions.PostgresDatabasesUpdate(),
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
                actions.FixMariadbDatabase(),
                actions.StartPleskBasicServices(),
            ],
        })

    if options.stage != Stages.finish:
        flow = actions.action.PrepareActionsFlow(actions_map)
    else:
        flow = actions.action.FinishActionsFlow(actions_map)

    flow.pass_actions()
