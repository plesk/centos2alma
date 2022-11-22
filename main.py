#!/usr/bin/python3
# Copyright 1999-2022. Plesk International GmbH. All rights reserved.

import actions

import sys
from optparse import OptionParser

if __name__ == "__main__":
    opts = OptionParser(usage="distupgrader [options] [stage]")
    opts.add_option("-s", "--stage", type='choice',
                    choices=('prepare', 'start', 'finish'),
                    help="Choose a stage of a convertation process. Prepare should be used before any other actions."
                         "Start - when you ready for a convertation process. The process will take about 20 minutes."
                         "Finish should be called at the end of convertation, right after the first reboot.")

    options, args = opts.parse_args(args=sys.argv[1:])

    actions_map = {}
    if options.stage != 'start':
        actions_map += {
            1: [
                actions.LeapInstallation()
            ],
            2: [
                actions.LeapReposConfiguration(),
                actions.LeapChoisesConfiguration(),
                actions.RemovingPackages(),
                actions.FixNamedConfig(),
                actions.DisableSuspiciousKernelModules(),
            ],
        }

    if opts.stage != 'prepare':
        actions_map += {
            2: [
                actions.RulePleskRelatedServices(),
                actions.RuleSelinux(),
            ],
            3: [
                actions.DoConvert(),
            ],
        }

    if opts.stage != 'stop':
        flow = actions.action.PrepareActionsFlow(actions_map)
    else:
        flow = actions.action.FinishActionsFlow(actions_map)

    flow.pass_actions()
