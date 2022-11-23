from .action import Action

import os

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


class LeapReposConfiguration(Action):

    def __init__(self):
        self.name = "add plesk to leapp repos mapping"

    def _prepare_action(self):
        mappings = []
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

    def _post_action(self):
        # Since only leap related files should be changed, there is no to do after a convertation
        pass


class LeapChoisesConfiguration(Action):

    def __init__(self):
        self.name = "configure leapp user choises"

    def _prepare_action(self):
        with open('/var/log/leapp/answerfile.userchoices', 'w') as usercoise:
            usercoise.write("[remove_pam_pkcs11_module_check]\nconfirm = True\n")

    def _post_action(self):
        # Since only leap related files should be changed, there is no to do after a convertation
        pass
