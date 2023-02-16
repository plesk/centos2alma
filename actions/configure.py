from .action import ActiveAction

import os
import shutil

from common import leapp_configs, files


class LeapReposConfiguration(ActiveAction):

    def __init__(self):
        self.name = "adding leapp mapping for plesk repositories"

    def _prepare_action(self):
        repofiles = []
        for file in os.scandir("/etc/yum.repos.d"):
            if file.name == "epel.repo":
                repofiles.append(file.path)

            if file.name.startswith("plesk") and file.name[-5:] == ".repo":
                repofiles.append(file.path)

        leapp_configs.add_repositories_mapping(repofiles, ignore=[
            "PLESK_17_PHP52", "PLESK_17_PHP53", "PLESK_17_PHP54",
            "PLESK_17_PHP55", "PLESK_17_PHP56", "PLESK_17_PHP70",
        ])

    def _post_action(self):
        # Since only leap related files should be changed, there is no to do after a conversation
        pass

    def _revert_action(self):
        pass


class LeapChoicesConfiguration(ActiveAction):

    def __init__(self):
        self.name = "configure leapp user choices"

    def _prepare_action(self):
        with open('/var/log/leapp/answerfile.userchoices', 'w') as usercoise:
            usercoise.write("[remove_pam_pkcs11_module_check]\nconfirm = True\n")

    def _post_action(self):
        # Since only leap related files should be changed, there is no to do after a conversation
        pass

    def _revert_action(self):
        pass


class LeapAddPostUpgradeActor(ActiveAction):

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
        self.name = "adding leapp post-upgrade actor"
        self.script_path = script_path

    def _prepare_action(self):
        if not os.path.exists(os.path.dirname(self.path)):
            os.mkdir(os.path.dirname(self.path), 0o755)

        with open(self.path, 'w') as actorfile:
            actorfile.write(self.actor_code.format(script_path=self.script_path))

    def _post_action(self):
        if os.path.exists(os.path.dirname(self.path)):
            shutil.rmtree(os.path.dirname(self.path))

    def _revert_action(self):
        pass


class PatchLeappErrorOutput(ActiveAction):

    def __init__(self):
        self.name = "patch leapp error log output"
        self.path_to_src = "/usr/share/leapp-repository/repositories/system_upgrade/common/libraries/dnfplugin.py"

    def _prepare_action(self):
        # Looks like there is no setter for stdout/stderr in the python for leapp
        files.replace_string(self.path_to_src, "if six.PY2:", "if False:")

    def _post_action(self):
        pass

    def _reverse_action(self):
        pass