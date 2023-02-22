import shutil
import json

import common


def remove_repositories(repofile, repositories):
    with open(repofile, "r") as original, open(repofile + ".next", "w") as dst:
        inRepo = False
        for line in original.readlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                if line[1:-1] in repositories:
                    inRepo = True
                else:
                    inRepo = False

            if not inRepo:
                dst.write(line + "\n")

    shutil.move(repofile + ".next", repofile)


def replace_string(filename, original_substring, new_substring):
    with open(filename, "r") as original, open(filename + ".next", "w") as dst:
        for line in original.readlines():
            line = line.replace(original_substring, new_substring)
            dst.write(line)

    shutil.move(filename + ".next", filename)


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
