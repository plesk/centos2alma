# Copyright 1999-2024. WebPros International GmbH. All rights reserved.
# vim:ft=python:

PRODUCT_VERSION = '1.4.2'

genrule(
    name = 'version',
    out = 'version.json',
    bash = r"""echo "{\"version\": \"%s\", \"revision\": \"`git rev-parse HEAD`\"}" > $OUT""" % (PRODUCT_VERSION),
)


python_binary(
    name = 'centos2alma.pex',
    platform = 'py3',
    build_args = ['--python-shebang', '/usr/bin/env python3'],
    main_module = 'centos2almaconverter.main',
    deps = [
        'dist-upgrader//pleskdistup:lib',
        '//centos2almaconverter:lib',
    ],
)

genrule(
    name = 'centos2alma',
    srcs = [':centos2alma.pex'],
    out = 'centos2alma',
    cmd = 'cp $(location :centos2alma.pex) $OUT && chmod +x $OUT',
)