import shutil
import json

import common


def replace_string(filename, original_substring, new_substring):
    with open(filename, "r") as original, open(filename + ".next", "w") as dst:
        for line in original.readlines():
            line = line.replace(original_substring, new_substring)
            if line:
                dst.write(line)

    shutil.move(filename + ".next", filename)


def rewrite_json_file(filename, jobj):
    if filename is None or jobj is None:
        return

    common.log.debug("Going to write json '{file}' with new data".format(file=filename))

    with open(filename + ".next", "w") as dst:
        dst.write(json.dumps(jobj, indent=4))

    shutil.move(filename + ".next", filename)