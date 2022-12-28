from .action import ActivaAction

import os
import shutil

from common import leapp_configs

# main_repo_format = """

# [alma-{name}]
# name=Alma {name}
# baseurl={url}
# enabled=1
# gpgcheck=1
# """

# epel_repos = """

# [alma-epel]
# name=Extra Packages for Enterprise Linux 8 - $basearch
# metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-8&arch=$basearch&infra=$infra&content=$contentdir
# failovermethod=priority
# enabled=1
# gpgcheck=1
# gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8

# [alma-epel-debuginfo]
# name=Extra Packages for Enterprise Linux 8 - $basearch - Debug
# metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-debug-8&arch=$basearch&infra=$infra&content=$contentdir
# failovermethod=priority
# enabled=0
# gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8
# gpgcheck=1

# [alma-epel-source]
# name=Extra Packages for Enterprise Linux 8 - $basearch - Source
# metalink=https://mirrors.fedoraproject.org/metalink?repo=epel-source-8&arch=$basearch&infra=$infra&content=$contentdir
# failovermethod=priority
# enabled=0
# gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-8
# gpgcheck=1
# """

# epel_mapping = """
# epel,alma-epel,alma-epel,all,all,x86_64,ga,ga
# epel-debuginfo,alma-epel-debuginfo,alma-epel-debuginfo,all,all,x86_64,ga,ga
# epel-source,alma-epel-source,alma-epel-source,all,all,x86_64,ga,ga
# """


class LeapReposConfiguration(ActivaAction):

    def __init__(self):
        self.name = "add plesk to leapp repos mapping"

    def _prepare_action(self):
        repofiles = []
        for file in os.scandir("/etc/yum.repos.d"):
            if file.name == "epel.repo":
                repofiles.append(file.path)

            if file.name.startswith("plesk") and file.name[-5:] == ".repo":
                repofiles.append(file.path)

        leapp_configs.add_repositories_mapping(repofiles)

        # mappings = []
        # with open("/etc/leapp/files/leapp_upgrade_repositories.repo", "a") as dst:
        #     looking_for_a_main = False
        #     main_repo_url = ""
        #     main_repo_name = ""

        #     for file in os.scandir("/etc/yum.repos.d"):
        #         if not file.name.startswith("plesk") or file.name[-5:] != ".repo":
        #             continue

        #         with open(file.path, "r") as repo:
        #             for line in repo.readlines():
        #                 if "rpm-CentOS-7" in line:
        #                     line = line.replace("rpm-CentOS-7", "rpm-RedHat-el8")

        #                 if line.startswith("[PLESK_18_0") and "extras" in line:
        #                     looking_for_a_main = True
        #                     main_repo_name = line.replace("-extras", "")[1:-2]
        #                     mappings.append((line[1:-2], "alma-" + main_repo_name))
        #                 if looking_for_a_main and line.startswith("baseurl="):
        #                     main_repo_url = line.replace("extras", "dist")[8:].rstrip()
        #                     looking_for_a_main = False

        #                 if line.startswith("["):
        #                     renamed_repo = line.replace("[", "[alma-")
        #                     mappings.append((line[1:-2], renamed_repo[1:-2]))
        #                     line = renamed_repo
        #                 elif line.startswith("name="):
        #                     line = line.replace("name=", "name=Alma ")

        #                 dst.write(line)
        #             dst.write("\n")

        #     dst.write(main_repo_format.format(name=main_repo_name, url=main_repo_url))
        #     dst.write(epel_repos)

        # with (open("/etc/leapp/files/repomap.csv", "a")) as dst:
        #     for mapping in mappings:
        #         dst.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=mapping[0], newrepo=mapping[1]))

        #     dst.write(epel_mapping)

    def _post_action(self):
        # Since only leap related files should be changed, there is no to do after a convertation
        pass


class LeapChoisesConfiguration(ActivaAction):

    def __init__(self):
        self.name = "configure leapp user choises"

    def _prepare_action(self):
        with open('/var/log/leapp/answerfile.userchoices', 'w') as usercoise:
            usercoise.write("[remove_pam_pkcs11_module_check]\nconfirm = True\n")

    def _post_action(self):
        # Since only leap related files should be changed, there is no to do after a convertation
        pass


class LeapAddPostUpgradeActor(ActivaAction):

    path = "/usr/share/leapp-repository/repositories/system_upgrade/common/actors/plesk/actor.py"
    actor_code = """
import subprocess
import sys

from leapp.actors import Actor
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import FirstBootPhaseTag, IPUWorkflowTag


class RemoveSystemdResumeService(Actor):
    \"\"\"
    Call post reboot actions related to plesk.
    \"\"\"

    name = 'call_plesk_post_convert'
    consumes = ()
    produces = (Report,)
    tags = (FirstBootPhaseTag.After, IPUWorkflowTag)

    def process(self):
        subprocess.Popen(["{script_path}", "-s", "finish"], stdout=sys.stdout, stderr=sys.stderr, start_new_session=True)

        create_report([
            reporting.Title('Plesk distupgrader has been spawned'),
            reporting.Summary('The script was taking care of all plesk related things'),
            reporting.Tags([reporting.Tags.UPGRADE_PROCESS]),
        ])

"""

    def __init__(self, script_path):
        self.name = "add leapp actor for the screapt autostartup"
        self.script_path = script_path

    def _prepare_action(self):
        if not os.path.exists(os.path.dirname(self.path)):
            os.mkdir(os.path.dirname(self.path), 0o755)

        with open(self.path, 'w') as actorfile:
            actorfile.write(self.actor_code.format(script_path=self.script_path))

    def _post_action(self):
        if os.path.exists(os.path.dirname(self.path)):
            shutil.rmtree(os.path.dirname(self.path))
