# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import fnmatch
import json
import os
import re
import shutil

import common


def replace_string(filename, original_substring, new_substring):
    with open(filename, "r") as original, open(filename + ".next", "w") as dst:
        for line in original.readlines():
            line = line.replace(original_substring, new_substring)
            dst.write(line)

    shutil.move(filename + ".next", filename)


def append_strings(filename, strings):
    next_file = filename + ".next"
    shutil.copy(filename, next_file)

    with open(next_file, "a") as dst:
        for string in strings:
            dst.write(string)

    shutil.move(next_file, filename)


def push_front_strings(filename, strings):
    next_file = filename + ".next"

    with open(filename, "r") as original, open(next_file, "w") as dst:
        for string in strings:
            dst.write(string)

        for line in original.readlines():
            dst.write(line)

    shutil.move(next_file, filename)


def rewrite_json_file(filename, jobj):
    if filename is None or jobj is None:
        return

    common.log.debug("Going to write json '{file}' with new data".format(file=filename))

    with open(filename + ".next", "w") as dst:
        dst.write(json.dumps(jobj, indent=4))

    shutil.move(filename + ".next", filename)


def get_last_lines(filename, n):
    with open(filename) as f:
        return f.readlines()[-n:]


def backup_file(filename):
    if os.path.exists(filename):
        shutil.copy(filename, filename + ".bak")


def restore_file_from_backup(filename, remove_if_no_backup=False):
    if os.path.exists(filename + ".bak"):
        shutil.move(filename + ".bak", filename)
    elif remove_if_no_backup and os.path.exists(filename):
        os.remove(filename)


def remove_backup(filename):
    if os.path.exists(filename + ".bak"):
        os.remove(filename + ".bak")


def __get_files_recursive(path):
    for root, _, files in os.walk(path):
        for file in files:
            yield os.path.relpath(os.path.join(root, file), path)


def find_files_case_insensitive(path, regexps_strings, recursive=False):
    # Todo. We should add typing for our functions
    if not isinstance(regexps_strings, list) and not isinstance(regexps_strings, str):
        raise TypeError("find_files_case_insensitive argument regexps_strings must be a list")
    # But string is a common mistake and we can handle it simply
    if isinstance(regexps_strings, str):
        regexps_strings = [regexps_strings]

    if not os.path.exists(path) or not os.path.isdir(path):
        return []

    result = []
    regexps = [re.compile(fnmatch.translate(r), re.IGNORECASE) for r in regexps_strings]
    files_list = __get_files_recursive(path) if recursive else os.listdir(path)

    for file in files_list:
        for regexp in regexps:
            if regexp.match(os.path.basename(file)):
                result.append(os.path.join(path, file))

    return result
