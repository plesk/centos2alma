# Copyright 1999-2024. WebPros International GmbH. All rights reserved.
# vim:ft=python:

PRODUCT_VERSION = '1.2.3'

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
    name = 'centos2alma.lib',
    srcs = glob(['main.py', 'messages.py']),
    deps = [
        ':actions.lib',
        '//common:common.lib',
    ],
    resources = [
        ':version',
    ],
)

python_binary(
    name = 'centos2alma-script',
    platform = 'py3',
    main_module = 'main',
    deps = [
        ':centos2alma.lib',
    ]
)

genrule(
    name = 'centos2alma',
    srcs = [':centos2alma-script'],
    out = 'centos2alma',
    cmd = 'cp $(location :centos2alma-script) $OUT && chmod +x $OUT',
)
