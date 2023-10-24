# Copyright 1999-2023. Plesk International GmbH. All rights reserved.
import os
import shutil

from common import action, files, log, motd, rpm

CPAN_MODULES_DIRECTORY = "/usr/local/lib64/perl5"
CPAN_MODULES_RPM_MAPPING = {
    "IO/Pty.pm": "perl-IO-Tty",
    "IO/Tty.pm": "perl-IO-Tty",
    "IO/Tty/Constant.pm": "perl-IO-Tty",
    "JSON/Syck.pm": "perl-YAML-Syck",
    "JSON/XS.pm": "perl-JSON-XS",
    "JSON/XS/Boolean.pm": "perl-JSON-XS",
    "YAML/Dumper/Syck.pm": "perl-YAML-Syck",
    "YAML/Loader/Syck.pm": "perl-YAML-Syck",
    "YAML/Syck.pm": "perl-YAML-Syck",
    "common/sense.pm": "perl-common-sense",
    "version.pm": "perl-version",
    "version/regex.pm": "perl-version",
    "version/vpp.pm": "perl-version",
    "version/vxs.pm": "perl-version",
    "Cwd.pm": "perl-PathTools",
    "File/Spec.pm": "perl-PathTools",
    "File/Spec/OS2.pm": "perl-PathTools",
    "File/Spec/Mac.pm": "perl-PathTools",
    "File/Spec/VMS.pm": "perl-PathTools",
    "File/Spec/Functions.pm": "perl-PathTools",
    "File/Spec/Cygwin.pm": "perl-PathTools",
    "File/Spec/Epoc.pm": "perl-PathTools",
    "File/Spec/Unix.pm": "perl-PathTools",
    "File/Spec/Win32.pm": "perl-PathTools",
    "File/Spec/AmigaOS.pm": "perl-PathTools",
}


class CheckUnknownPerlCpanModules(action.CheckAction):
    def __init__(self):
        self.name = "checking if there are no unknown perl cpan modules"
        self.description = """There are Perl modules installed by CPAN without known RPM package analogues are found.
\tPlease remove following modules manually from "{directory}" and reinstall them after the conversion:
\t- {modules_list}

\tThe centos2alma tool is unable to handle these modules automatically as it does not have information about the RPM package analogues for them.
\tIf you know the RPM analogues for these modules, please contact us at https://github.com/plesk/centos2alma/issues.

\tYou can use the flag --remove-unknown-perl-modules to remove all of these modules automatically and force the conversion.
\tPlease note that removing these modules may cause issues with Perl scripts.
"""

    def _do_check(self):
        if not os.path.exists(CPAN_MODULES_DIRECTORY):
            return True

        unknown_modules = []
        for module in files.find_files_case_insensitive(CPAN_MODULES_DIRECTORY, ["*.pm"], recursive=True):
            module = os.path.relpath(module, CPAN_MODULES_DIRECTORY)
            if module not in CPAN_MODULES_RPM_MAPPING.keys():
                unknown_modules.append(module)

        if not unknown_modules:
            return True

        self.description = self.description.format(directory=CPAN_MODULES_DIRECTORY, modules_list="\n\t- ".join(unknown_modules))
        return False


class ReinstallPerlCpanModules(action.ActiveAction):
    def __init__(self):
        self.name = "reinstalling perl cpan modules"
        self.removed_modules_file = "/tmp/centos2alma_removed_perl_modules.txt"

    def _is_required(self):
        return not files.is_directory_empty(CPAN_MODULES_DIRECTORY)

    def _prepare_action(self):
        with open(self.removed_modules_file, "w") as f:
            for module in files.find_files_case_insensitive(CPAN_MODULES_DIRECTORY, ["*.pm"], recursive=True):
                if module in CPAN_MODULES_RPM_MAPPING.keys():
                    f.write(CPAN_MODULES_RPM_MAPPING[module] + "\n")

        # Yeah it's preatty rude to remove all isntalled modules,
        # but cpan don't have an option to remove one module for some reason.
        # Since we can't be sure cpan-minimal is installed, we have to
        # remove all in barbaric way.
        shutil.move(CPAN_MODULES_DIRECTORY, CPAN_MODULES_DIRECTORY + ".backup")

    def _post_action(self):
        if not os.path.exists(self.removed_modules_file):
            no_file_warning = "The file containing the list of removed Perl modules does not exist. However, the action itself was not skipped. You can find the previously installed modules at the following path: {}.".format(CPAN_MODULES_DIRECTORY + ".backup")
            log.warn(no_file_warning)
            motd.add_finish_ssh_login_message(no_file_warning)
            return

        with open(self.removed_modules_file, "r") as f:
            packages_to_install = f.read().splitlines()
            rpm.install_packages(packages_to_install)

        os.unlink(self.removed_modules_file)
        shutil.rmtree(CPAN_MODULES_DIRECTORY + ".backup")

    def _revert_action(self):
        shutil.move(CPAN_MODULES_DIRECTORY + ".backup", CPAN_MODULES_DIRECTORY)
        os.unlink(self.removed_modules_file)

    def estimate_post_time(self):
        return 60
