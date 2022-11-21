#!/usr/bin/python3
# Copyright 1999-2022. Plesk International GmbH. All rights reserved.

import os
import shutil
import subprocess

import actions

def install_leapp():
    pkgs_to_install = [
        "http://repo.almalinux.org/elevate/elevate-release-latest-el7.noarch.rpm",
        "leapp-upgrade",
        "leapp-data-almalinux",
    ]

    subprocess.check_call(["yum", "install", "-y"] + pkgs_to_install)


def patch_leapp():
    pass

main_repo_format = """

[alma-{name}]
name=Alma {name}
baseurl={url}
enabled=1
gpgcheck=1
"""

epel_repos = """

[alma-epel]
name=Extra Packages for Enterprise Linux 8 - $basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-8&arch=$basearch&infra=$infra&content=$contentdir
failovermethod=priority
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8

[alma-epel-debuginfo]
name=Extra Packages for Enterprise Linux 8 - $basearch - Debug
metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-debug-8&arch=$basearch&infra=$infra&content=$contentdir
failovermethod=priority
enabled=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8
gpgcheck=1

[alma-epel-source]
name=Extra Packages for Enterprise Linux 8 - $basearch - Source
metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-source-8&arch=$basearch&infra=$infra&content=$contentdir
failovermethod=priority
enabled=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8
gpgcheck=1
"""

epel_mapping = """
epel,alma-epel,alma-epel,all,all,x86_64,ga,ga
epel-debuginfo,alma-epel-debuginfo,alma-epel-debuginfo,all,all,x86_64,ga,ga
epel-source,alma-epel-source,alma-epel-source,all,all,x86_64,ga,ga
"""

mappings = []

def configure_leapp_repos():
    with open("/etc/leapp/files/leapp_upgrade_repositories.repo", "a") as dst:
        looking_for_a_main = False
        main_repo_url = ""
        main_repo_name = ""

        for file in os.scandir("/etc/yum.repos.d"):
            if not file.name.startswith("plesk") or file.name[-5:] != ".repo":
                continue

            with open(file.path, "r") as repo:
                for line in repo.readlines():
                    if "rpm-CentOS-7" in line:
                        line = line.replace("rpm-CentOS-7", "rpm-RedHat-el8")

                    if line.startswith("[PLESK_18_0") and "extras" in line:
                        looking_for_a_main = True
                        main_repo_name = line.replace("-extras", "")[1:-2]
                        mappings.append((line[1:-2], "alma-" + main_repo_name))
                    if looking_for_a_main and line.startswith("baseurl="):
                        main_repo_url = line.replace("extras", "dist")[8:].rstrip()
                        looking_for_a_main = False

                    if line.startswith("["):
                        renamed_repo = line.replace("[", "[alma-")
                        mappings.append((line[1:-2], renamed_repo[1:-2]))
                        line = renamed_repo
                    elif line.startswith("name="):
                        line = line.replace("name=", "name=Alma ")

                    dst.write(line)

        dst.write(main_repo_format.format(name=main_repo_name, url=main_repo_url))
        dst.write(epel_repos)

    with (open("/etc/leapp/files/repomap.csv", "a")) as dst:
        for mapping in mappings:
            dst.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=mapping[0], newrepo=mapping[1]))

        dst.write(epel_mapping)

def configure_leapp():
    with open('/var/log/leapp/answerfile.userchoices', 'w') as usercoise:
        usercoise.write("[remove_pam_pkcs11_module_check]\nconfirm = True\n")

    configure_leapp_repos()


def remove_conflict_packages():
    pkgs=[
        "openssl11-libs",
        "python36-PyYAML",
        "GeoIP",
        "psa-mod_proxy",
        "plesk-roundcube",
        "psa-phpmyadmin",
    ]

    for pkg in pkgs:
        subprocess.check_call(["rpm", "-e", "--nodeps"] + pkg)


def prepare_system():
    os.symlink("/var/named/chroot/etc/named-user-options.conf", "/etc/named-user-options.conf")

    plesk_systemcd_services = [
        "dovecot.service",
        "fail2ban.service",
        "httpd.service",
        "mariadb.service",
        "named-chroot.service",
        "plesk-ext-monitoring-hcd.service",
        "plesk-ip-remapping.service",
        "plesk-ssh-terminal.service",
        "plesk-task-manager.service",
        "plesk-web-socket.service",
        "postfix.service",
        "psa.service",
        "sw-collectd.service",
        "sw-cp-server.service",
        "sw-engine.service",
    ]
    subprocess.check_call(["systemctl", "stop"] + plesk_systemcd_services)
    subprocess.check_call(["systemctl", "disable"] + plesk_systemcd_services)


def preconfig_kernel():

    modules_to_ban = ["pata_acpi", "btrfs"]

    with open("/etc/modprobe.d/pataacpibl.conf", "a") as kern_mods_config:
        for module in modules_to_ban:
            kern_mods_config.write("blacklist {module}\n".format(module))

        subprocess.check_call(["rmmod", module])



def replace_string(filename, original_substring, new_substring):
    with open(filename, "r") as original, open(filename + ".next", "w") as dst:
        for line in original.readlines():
            dst.write(line.replace(original_substring, new_substring))

    shutil.move(filename + ".next", filename)



def disable_selinux():
    replace_string("/etc/selinux/config", "SELINUX=enforcing", "SELINUX=permissive")


def pre_convert():
    install_leapp()
    patch_leapp()
    configure_leapp()
    remove_conflict_packages()
    prepare_system()
    preconfig_kernel()
    disable_selinux()


def do_convert():
    pass


def post_convert():
    pass

if __name__ == "__main__":
    print ("Hello!!")
    print(dir(actions))
    print(actions.__file__)
    a = actions.action.Action()
    # a = action.Action()
    print(a)

    # pre_convert()

    # do_convert()

    # post_convert()