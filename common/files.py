# Copyright 1999 - 2023. Plesk International GmbH. All rights reserved.
import fnmatch
import json
import os
import re
import shutil
import typing

import common


def replace_string(filename: str, original_substring: str, new_substring: str) -> None:
    with open(filename, "r") as original, open(filename + ".next", "w") as dst:
        for line in original.readlines():
            line = line.replace(original_substring, new_substring)
            dst.write(line)

    shutil.move(filename + ".next", filename)


def append_strings(filename: str, strings: typing.List[str]) -> None:
    next_file = filename + ".next"
    shutil.copy(filename, next_file)

    with open(next_file, "a") as dst:
        for string in strings:
            dst.write(string)

    shutil.move(next_file, filename)


def push_front_strings(filename: str, strings: typing.List[str]) -> None:
    next_file = filename + ".next"

    with open(filename, "r") as original, open(next_file, "w") as dst:
        for string in strings:
            dst.write(string)

        for line in original.readlines():
            dst.write(line)

    shutil.move(next_file, filename)


def rewrite_json_file(filename: str, jobj: typing.Union[dict, typing.List]) -> None:
    if filename is None or jobj is None:
        return

    common.log.debug("Going to write json '{file}' with new data".format(file=filename))

    with open(filename + ".next", "w") as dst:
        dst.write(json.dumps(jobj, indent=4))

    shutil.move(filename + ".next", filename)


def get_last_lines(filename: str, n: int) -> typing.List[str]:
    with open(filename) as f:
        return f.readlines()[-n:]


def backup_file(filename: str) -> None:
    if os.path.exists(filename):
        shutil.copy(filename, filename + ".bak")


def restore_file_from_backup(filename: str, remove_if_no_backup: bool = False) -> None:
    if os.path.exists(filename + ".bak"):
        shutil.move(filename + ".bak", filename)
    elif remove_if_no_backup and os.path.exists(filename):
        os.remove(filename)


def remove_backup(filename: str) -> None:
    if os.path.exists(filename + ".bak"):
        os.remove(filename + ".bak")


def __get_files_recursive(path: str) -> typing.Iterator[str]:
    for root, _, files in os.walk(path):
        for file in files:
            yield os.path.relpath(os.path.join(root, file), path)


def find_files_case_insensitive(path: str, regexps_strings: typing.Union[typing.List, str], recursive: bool = False):
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


def is_directory_empty(path: str):
    return not os.path.exists(path) or len(os.listdir(path)) == 0


def find_subdirectory_by(directory: str, functor: typing.Callable[[str], bool]) -> str:
    for root, directories, _ in os.walk(directory):
        for subdir in directories:
            fullpath = os.path.join(root, subdir)
            if functor(fullpath):
                return fullpath
    return None
