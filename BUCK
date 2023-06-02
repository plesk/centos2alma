# Copyright 1999-2023. Plesk International GmbH. All rights reserved.
# vim:ft=python:

PRODUCT_VERSION = '0.2.0'

genrule(
    name = 'version',
    out = 'version.json',
    bash = r"""echo "{\"version\": \"%s\", \"revision\": \"`git rev-parse HEAD`\"}" > $OUT""" % (PRODUCT_VERSION),
)

python_library(
    name = 'actions.lib',
    srcs = glob(['./actions/*.py']),
)

python_library(
    name = 'common.lib',
    srcs = glob(['./common/*.py']),
)

python_library(
    name = 'libs.lib',
    srcs = glob(['main.py']),
    deps = [
        ':actions.lib',
        ':common.lib',
    ],
    resources = [
        ':version',
    ],
)

python_test(
    name = 'libs.tests',
    srcs = glob(['./tests/*.py']),
    deps = [
        ':common.lib',
        ':actions.lib',
    ],
    platform = 'py3',
)

python_binary(
    name = 'centos2alma-script',
    platform = 'py3',
    main_module = 'main',
    deps = [
        ':libs.lib',
    ]
)

genrule(
    name = 'centos2alma',
    srcs = [':centos2alma-script'],
    out = 'centos2alma',
    cmd = 'cp $(location :centos2alma-script) $OUT && chmod +x $OUT',
)
