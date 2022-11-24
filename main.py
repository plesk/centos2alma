#!/usr/bin/python3
# Copyright 1999-2022. Plesk International GmbH. All rights reserved.

import actions

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
    opts = OptionParser(usage="distupgrader [options] [stage]")
    opts.add_option("-s", "--stage", type='choice',
                    choices=(Stages.prepare, Stages.convert, Stages.finish),
                    help="Choose a stage of a convertation process. Prepare should be used before any other actions."
                         "Start - when you ready for a convertation process. The process will take about 20 minutes."
                         "Finish should be called at the end of convertation, right after the first reboot.")

    options, args = opts.parse_args(args=sys.argv[1:])

    actions_map = {}
    if not options.stage or options.stage == Stages.prepare or options.stage == Stages.finish:
        actions_map = merge_dicts_of_lists(actions_map, {
            1: [
                actions.LeapInstallation(),
            ],
            2: [
                actions.LeapReposConfiguration(),
                actions.LeapChoisesConfiguration(),
                actions.LeapAddPostUpgradeActor(os.path.abspath(sys.argv[0])),
                actions.FixNamedConfig(),
            ],
        })

    if not options.stage or options.stage == Stages.convert or options.stage == Stages.finish:
        actions_map = merge_dicts_of_lists(actions_map, {
            2: [
                actions.RemovingPackages(),
                actions.FixupWebmail(),
                actions.DisableSuspiciousKernelModules(),
                actions.RulePleskRelatedServices(),
                actions.RuleSelinux(),
            ],
            3: [
                actions.DoConvert(),
            ],
        })
    if options.stage == Stages.finish:
        actions_map = merge_dicts_of_lists(actions_map, {
            3: [
                actions.AdoptPleskRepositories(),
            ],
        })

    if options.stage != Stages.finish:
        flow = actions.action.PrepareActionsFlow(actions_map)
    else:
        flow = actions.action.FinishActionsFlow(actions_map)

    flow.pass_actions()
