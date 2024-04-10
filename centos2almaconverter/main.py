#!/usr/bin/python3
# Copyright 1999-2024. Plesk International GmbH. All rights reserved.

import sys

import pleskdistup.main
import pleskdistup.registry

import centos2almaconverter.upgrader

if __name__ == "__main__":
    pleskdistup.registry.register_upgrader(centos2almaconverter.upgrader.Centos2AlmaConverterFactory())
    sys.exit(pleskdistup.main.main())
