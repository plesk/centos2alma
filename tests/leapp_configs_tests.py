import unittest
import os
import json
import typing

from common import leapp_configs


class AddMappingTests(unittest.TestCase):

    LEAPP_REPO_FILE = "leapp_repos.repo"
    LEAPP_MAP_FILE = "map.repo"

    def tearDown(self):
        for files in (self.LEAPP_REPO_FILE, self.LEAPP_MAP_FILE):
            if os.path.exists(files):
                os.remove(files)

    def _perform_test(self, repos: typing.Dict[str, str], expected_repos: str, expected_mapping: str, ignore: bool = None) -> None:
        for filename, content in repos.items():
            with open(filename, "w") as f:
                f.write(content)

        leapp_configs.add_repositories_mapping(repos, ignore=ignore,
                                               leapp_repos_file_path=self.LEAPP_REPO_FILE,
                                               mapfile_path=self.LEAPP_MAP_FILE)

        with open(self.LEAPP_REPO_FILE) as f:
            lines = [line.rstrip() for line in f.readlines() if not line.rstrip() == ""]
            print(lines)
            self.assertEqual(lines, expected_repos.splitlines())

        with open(self.LEAPP_MAP_FILE) as f:
            lines = [line.rstrip() for line in f.readlines() if not line.rstrip() == ""]
            self.assertEqual(lines, expected_mapping.splitlines())

        for files in repos.keys():
            if os.path.exists(files):
                os.remove(files)

    def test_simple_mapping(self):
        simple_repos = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0
#no comment removed

[repo2]
name=repo2
baseurl=http://repo2/rpm-CentOS-7
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3/centos7
enabled=1
gpgcheck=0
"""

        expected_leapp_repos = """[alma-repo1]
name=Alma repo1
baseurl=http://repo1
enabled=1
gpgcheck=0
#no comment removed
[alma-repo2]
name=Alma repo2
baseurl=http://repo2/rpm-RedHat-el8
enabled=1
gpgcheck=0
[alma-repo3]
name=Alma repo3
baseurl=http://repo3/centos8
enabled=1
gpgcheck=0
"""
        expected_leapp_mapping = """repo1,alma-repo1,alma-repo1,all,all,x86_64,rpm,ga,ga
repo2,alma-repo2,alma-repo2,all,all,x86_64,rpm,ga,ga
repo3,alma-repo3,alma-repo3,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"simple_repos.repo": simple_repos},
                           expected_leapp_repos, expected_leapp_mapping)

    def test_kolab_related_mapping(self):
        kolab_repos = """[kolab-repo]
name=Kolab repo
baseurl=https://mirror.apheleia-it.ch/repos/Kolab:/16/CentOS_7_Plesk_17/src
enabled=0
priority=60
skip_if_unavailable=1
gpgcheck=1
"""

        expected_kolab_leapp_repos = """[alma-kolab-repo]
name=Alma Kolab repo
baseurl=https://mirror.apheleia-it.ch/repos/Kolab:/16/CentOS_8_Plesk_17/src
enabled=0
priority=60
skip_if_unavailable=1
gpgcheck=1
"""

        expected_kolab_leapp_mapping = """kolab-repo,alma-kolab-repo,alma-kolab-repo,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"kolab.repo": kolab_repos},
                           expected_kolab_leapp_repos, expected_kolab_leapp_mapping)

    def test_epel_mapping(self):
        epel_like_repos = """[epel-repo]
name=EPEL-7 repo
metalink=http://epel-repo/epel-7
enabled=1
gpgcheck=0

[epel-debug-repo]
name=EPEL-7 debug repo
metalink=http://epel-repo/epel-debug-7
enabled=1
gpgcheck=0

[epel-source-repo]
name=EPEL-7 source repo
metalink=http://epel-repo/epel-source-7
enabled=1
gpgcheck=0
"""
        expected_leapp_repos = """[alma-epel-repo]
name=Alma EPEL-8 repo
metalink=http://epel-repo/epel-8
enabled=1
gpgcheck=0
[alma-epel-debug-repo]
name=Alma EPEL-8 debug repo
metalink=http://epel-repo/epel-debug-8
enabled=1
gpgcheck=0
[alma-epel-source-repo]
name=Alma EPEL-8 source repo
metalink=http://epel-repo/epel-source-8
enabled=1
gpgcheck=0
"""
        expected_leapp_mapping = """epel-repo,alma-epel-repo,alma-epel-repo,all,all,x86_64,rpm,ga,ga
epel-debug-repo,alma-epel-debug-repo,alma-epel-debug-repo,all,all,x86_64,rpm,ga,ga
epel-source-repo,alma-epel-source-repo,alma-epel-source-repo,all,all,x86_64,rpm,ga,ga
"""
        self._perform_test({"epel_repos.repo": epel_like_repos},
                           expected_leapp_repos, expected_leapp_mapping)

    def test_plesk_mapping(self):
        plesk_like_repos = """[PLESK_18_0_XX-extras]
name=plesk extras repo
baseurl=http://plesk/rpm-CentOS-7/extras
enabled=1
gpgcheck=0

[PLESK_18_0_XX-PHP-5.5]
name=plesk php 5.5 repo
baseurl=http://plesk/rpm-CentOS-7/php-5.5
enabled=1
gpgcheck=0

[PLESK_18_0_XX-PHP72]
name=plesk php 7.2 repo
baseurl=http://plesk/rpm-CentOS-7/PHP_7.2
enabled=1
gpgcheck=0

[PLESK_18_0_XX-PHP80]
name=plesk php 8.0 repo
baseurl=http://plesk/rpm-CentOS-7/PHP_8.0
enabled=1
gpgcheck=0
"""
        expected_leapp_repos = """[alma-PLESK_18_0_XX-extras]
name=Alma plesk extras repo
baseurl=http://plesk/rpm-RedHat-el8/extras
enabled=1
gpgcheck=0
[alma-PLESK_18_0_XX]
name=Alma plesk  repo
baseurl=http://plesk/rpm-RedHat-el8/dist
enabled=1
gpgcheck=1
[alma-PLESK_18_0_XX-PHP72]
name=Alma plesk php 7.2 repo
baseurl=http://plesk/rpm-CentOS-8/PHP_7.2
enabled=1
gpgcheck=0
[alma-PLESK_18_0_XX-PHP80]
name=Alma plesk php 8.0 repo
baseurl=http://plesk/rpm-RedHat-el8/PHP_8.0
enabled=1
gpgcheck=0
"""
        expected_leapp_mapping = """PLESK_18_0_XX-extras,alma-PLESK_18_0_XX,alma-PLESK_18_0_XX,all,all,x86_64,rpm,ga,ga
PLESK_18_0_XX-extras,alma-PLESK_18_0_XX-extras,alma-PLESK_18_0_XX-extras,all,all,x86_64,rpm,ga,ga
PLESK_18_0_XX-PHP72,alma-PLESK_18_0_XX-PHP72,alma-PLESK_18_0_XX-PHP72,all,all,x86_64,rpm,ga,ga
PLESK_18_0_XX-PHP80,alma-PLESK_18_0_XX-PHP80,alma-PLESK_18_0_XX-PHP80,all,all,x86_64,rpm,ga,ga
"""

        self._perform_test({"plesk_repos.repo": plesk_like_repos},
                           expected_leapp_repos, expected_leapp_mapping,
                           ignore=["PLESK_18_0_XX-PHP-5.5"])


class SetPackageRepositoryTests(unittest.TestCase):
    INITIAL_JSON = {
        "packageinfo": [
            {
                "in_packageset": {
                    "package": [
                        {
                            "name": "some",
                            "repository": "some-repo",
                        },
                    ],
                },
                "out_packageset": {
                    "package": [
                        {
                            "name": "some",
                            "repository": "other-repo",
                        },
                    ],
                },
            },
            {
                "in_packageset": {
                    "package": [
                        {
                            "name": "other",
                            "repository": "some-repo",
                        },
                    ],
                },
                "out_packageset": {
                    "package": [
                        {
                            "name": "other",
                            "repository": "other-repo",
                        },
                    ],
                },
            }
        ]
    }

    JSON_FILE_PATH = "leapp_upgrade_repositories.json"
    # Since json could take pretty much symbols remove the restriction
    maxDiff = None

    def setUp(self):
        with open(self.JSON_FILE_PATH, "w") as f:
            f.write(json.dumps(self.INITIAL_JSON, indent=4))

    def tearDown(self):
        if os.path.exists(self.JSON_FILE_PATH):
            os.remove(self.JSON_FILE_PATH)
        pass

    def test_set_package_repository(self):
        leapp_configs.set_package_repository("some", "alma-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data["packageinfo"][0]["out_packageset"]["package"][0]["repository"], "alma-repo")
            self.assertEqual(json_data["packageinfo"][1]["out_packageset"]["package"][0]["repository"], "other-repo")

    def test_set_unexcited_package(self):
        leapp_configs.set_package_repository("unexsisted", "alma-repo", leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH, "r") as f:
            json_data = json.load(f)
            print(json_data)
            print(self.INITIAL_JSON)
            self.assertEqual(json_data, self.INITIAL_JSON)


class SetPackageActionTests(unittest.TestCase):
    INITIAL_JSON = {
        "packageinfo": [
            {
                "action": 1,
                "in_packageset": {
                    "package": [
                        {
                            "name": "some",
                            "repository": "some-repo",
                        },
                    ],
                },
            },
            {
                "action": 4,
                "in_packageset": {
                    "package": [
                        {
                            "name": "other",
                            "repository": "some-repo",
                        },
                    ],
                },
            }
        ]
    }

    JSON_FILE_PATH = "leapp_upgrade_repositories.json"
    # Since json could take pretty much symbols remove the restriction
    maxDiff = None

    def setUp(self):
        with open(self.JSON_FILE_PATH, "w") as f:
            f.write(json.dumps(self.INITIAL_JSON, indent=4))

    def tearDown(self):
        if os.path.exists(self.JSON_FILE_PATH):
            os.remove(self.JSON_FILE_PATH)
        pass

    def test_set_package_action(self):
        leapp_configs.set_package_action("some", 3, leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH) as f:
            json_data = json.load(f)
            self.assertEqual(json_data["packageinfo"][0]["action"], 3)
            self.assertEqual(json_data["packageinfo"][1]["action"], 4)

    def test_set_unexcited_package_action(self):
        leapp_configs.set_package_action("unexsisted", 3, leapp_pkgs_conf_path=self.JSON_FILE_PATH)

        with open(self.JSON_FILE_PATH, "r") as f:
            json_data = json.load(f)
            self.assertEqual(json_data, self.INITIAL_JSON)
