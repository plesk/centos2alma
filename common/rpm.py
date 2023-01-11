import subprocess


def filter_installed_packages(lookup_pkgs):
    pkgs = []
    process = subprocess.run(["rpm", "-q", "-a"], stdout=subprocess.PIPE, universal_newlines=True)
    for line in process.stdout.splitlines():
        end_of_name = 0
        while end_of_name != -1:
            end_of_name = line.find("-", end_of_name + 1)
            if line[end_of_name + 1].isnumeric():
                break

        if end_of_name == -1:
            continue

        pkg_name = line[:end_of_name]
        if pkg_name in lookup_pkgs:
            pkgs.append(pkg_name)
    return pkgs


def is_package_installed(pkg):
    res = subprocess.run(["rpm", "--quiet", "--query", pkg])
    return res.returncode == 0


def remove_packages(pkg):
    subprocess.check_call(["rpm", "-e", "--nodeps", pkg])
