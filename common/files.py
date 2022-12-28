import shutil
import json


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

    with open(filename + ".next", "w") as dst:
        dst.write(json.dumps(jobj, indent=4))

    shutil.move(filename + ".next", filename)