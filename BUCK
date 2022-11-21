# Copyright 1999-2022. Plesk International GmbH. All rights reserved.
# vim:ft=python:

include_defs('//buck-rules/third-party/py/pathlib/pathlib.py')

python_library(
    name = 'actions.lib',
    srcs = glob(['./actions/*.py'])
)

python_library(
    name = 'distupgrader.lib',
    srcs = glob(['main.py']),
    deps = [
        ':actions.lib',
    ],
)

python_binary(
    name = 'distupgrader',
    platform = 'py3',
    main_module = 'main',
    deps = [
        ':distupgrader.lib',
    ]
)
