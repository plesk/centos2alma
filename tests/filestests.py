import unittest
import os
import json
import tempfile
import shutil

from common import files


class ReplaceFileStringTests(unittest.TestCase):
    REPLACE_FILE_CONTENT = """---> cccc <---
This is the file where we want to replace some string. This is the string to replace ---> aaaa <---.
---> eeee <---
---> gggg <---
"""

    DATA_FILE_NAME = "datafile.txt"

    def setUp(self):
        with open(self.DATA_FILE_NAME, "w") as f:
            f.write(self.REPLACE_FILE_CONTENT)

    def tearDown(self):
        if os.path.exists(self.DATA_FILE_NAME):
            os.remove(self.DATA_FILE_NAME)

    def test_simple_string_replace(self):
        files.replace_string(self.DATA_FILE_NAME, "aaaa", "bbbb")
        with open(self.DATA_FILE_NAME) as file:
            for line in file.readlines():
                if line.startswith("This is the string to replace"):
                    self.assertEqual(line, "This is the file where we want to replace some string. This is the string to replace ---> bbbb <---.")
                    break

    def test_replace_first_string(self):
        files.replace_string(self.DATA_FILE_NAME, "---> cccc <---", "<--- dddd --->")
        with open(self.DATA_FILE_NAME) as file:
            self.assertEqual(file.readline().rstrip(), "<--- dddd --->")

    def test_replace_whole_line(self):
        files.replace_string(self.DATA_FILE_NAME, "---> eeee <---", "<--- ffff --->")
        with open(self.DATA_FILE_NAME) as file:
            line = file.readlines()[-2].rstrip()
            self.assertEqual(line, "<--- ffff --->")

    def test_replase_last_string(self):
        files.replace_string(self.DATA_FILE_NAME, "---> gggg <---", "<--- hhhh --->")
        with open(self.DATA_FILE_NAME) as file:
            line = file.readlines()[-1].rstrip()
            self.assertEqual(line, "<--- hhhh --->")


class AppendStringsTests(unittest.TestCase):
    ORIGINAL_FILE_NAME = "original.txt"

    def setUp(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("")

    def tearDown(self):
        if os.path.exists(self.ORIGINAL_FILE_NAME):
            os.remove(self.ORIGINAL_FILE_NAME)

    def test_add_to_empty(self):
        files.append_strings(self.ORIGINAL_FILE_NAME, ['aaaa\n', 'bbbb\n'])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ['aaaa', 'bbbb'])

    def test_add_to_non_empty(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("aaaa\n")
        files.append_strings(self.ORIGINAL_FILE_NAME, ["bbbb\n", "cccc\n"])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["aaaa", "bbbb", "cccc"])

    def test_add_nothing(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("aaaa\n")
        files.append_strings(self.ORIGINAL_FILE_NAME, [])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["aaaa"])


class PushFrontStringsTests(unittest.TestCase):
    ORIGINAL_FILE_NAME = "original.txt"

    def setUp(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("")

    def tearDown(self):
        if os.path.exists(self.ORIGINAL_FILE_NAME):
            os.remove(self.ORIGINAL_FILE_NAME)

    def test_add_to_empty(self):
        files.push_front_strings(self.ORIGINAL_FILE_NAME, ["aaaa\n", "bbbb\n"])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["aaaa", "bbbb"])

    def test_add_to_non_empty(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("aaaa\n")
        files.push_front_strings(self.ORIGINAL_FILE_NAME, ["bbbb\n", "cccc\n"])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["bbbb", "cccc", "aaaa"])

    def test_add_nothing(self):
        with open(self.ORIGINAL_FILE_NAME, "w") as f:
            f.write("aaaa\n")
        files.push_front_strings(self.ORIGINAL_FILE_NAME, [])
        with open(self.ORIGINAL_FILE_NAME) as f:
            self.assertEqual([line.rstrip() for line in f.readlines()], ["aaaa"])


class RewriteJsonTests(unittest.TestCase):
    OriginalJson = {
        "key1": "value1",
        "obj": {
            "key2": "value2",
        },
        "array": [
            "value3",
            "value4",
            "value5",
        ],
        "objs": [
            {
                "sharedkey": "value6",
            },
            {
                "sharedkey": "value7",
            }
        ],
    }
    INITIAL_JSON_FILE_NAME = "test.json"

    def setUp(self):
        with open(self.INITIAL_JSON_FILE_NAME, "w") as f:
            f.write(json.dumps(self.OriginalJson))

    def tearDown(self):
        if os.path.exists(self.INITIAL_JSON_FILE_NAME):
            os.remove(self.INITIAL_JSON_FILE_NAME)

    def test_simple_json_rewrite(self):
        new_json = {
            "key1": "newvalue",
            "obj": {
                "key2": "newvalue2",
            },
            "array": [
                "newvalue3",
                "newvalue4",
                "newvalue5",
            ],
            "objs": [
                {
                    "sharedkey": "newvalue6",
                },
                {
                    "sharedkey": "newvalue7",
                }
            ],
        }
        new_json["key1"] = "newvalue"
        files.rewrite_json_file(self.INITIAL_JSON_FILE_NAME, new_json)
        with open(self.INITIAL_JSON_FILE_NAME) as file:
            self.assertEqual(json.load(file), new_json)


class RemoveRepositoriesTests(unittest.TestCase):
    REPO_FILE_CONTENT = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
baseurl=http://repo2
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""

    REPO_FILE_NAME = "repo_file.txt"

    def setUp(self):
        with open(self.REPO_FILE_NAME, "w") as f:
            f.write(self.REPO_FILE_CONTENT)

    def tearDown(self):
        if os.path.exists(self.REPO_FILE_NAME):
            os.remove(self.REPO_FILE_NAME)

    def test_remove_first_repo(self):
        expected_content = """[repo2]
name=repo2
baseurl=http://repo2
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""

        files.remove_repositories(self.REPO_FILE_NAME, ["repo1"])

        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_multiple_repos(self):
        expected_content = """[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""

        files.remove_repositories(self.REPO_FILE_NAME, ["repo1", "repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_all_repos(self):
        files.remove_repositories(self.REPO_FILE_NAME, ["repo1", "repo2", "repo3"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.readlines(), [])

    def test_remove_non_existing_repo(self):
        files.remove_repositories(self.REPO_FILE_NAME, ["repo4"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), self.REPO_FILE_CONTENT)

    def test_remove_last_repo(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo2]
name=repo2
baseurl=http://repo2
enabled=1
gpgcheck=0

"""

        files.remove_repositories(self.REPO_FILE_NAME, ["repo3"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)


class FindFilesCaseInsensativeTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_find_file(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["file.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["file.txt"])

    def test_find_file_with_different_case(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["FILE.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["file.txt"])

    def test_find_several_files_by_extension(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file2.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file.md"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["*.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["file.txt", "file2.txt"])

    def test_find_different_case_files(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "FILE.txt"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["file.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["FILE.txt", "file.txt"])

    def test_find_different_case_files_by_extension(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "FILE.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file.md"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["f*.txt"]))
        self.assertEqual([os.path.basename(file) for file in result], ["FILE.txt", "file.txt"])

    def test_empty_directory(self):
        self.assertEqual(files.find_files_case_insensitive(self.temp_dir, ["file.txt"]), [])

    def test_find_no_files_by_extension(self):
        self.assertEqual(files.find_files_case_insensitive(self.temp_dir, ["*.txt"]), [])

    def test_find_no_files(self):
        with open(os.path.join(self.temp_dir, "file.md"), "w") as f:
            f.write("")

        self.assertEqual(files.find_files_case_insensitive(self.temp_dir, ["file.txt"]), [])

    def test_no_such_directory(self):
        self.assertEqual(files.find_files_case_insensitive(os.path.join(self.temp_dir, "no_such_dir"), ["file.txt"]), [])

    def test_several_regexps(self):
        with open(os.path.join(self.temp_dir, "file.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file2.txt"), "w") as f:
            f.write("")
        with open(os.path.join(self.temp_dir, "file.md"), "w") as f:
            f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["file.txt", "*.md"]))
        self.assertEqual([os.path.basename(file) for file in result], ["file.md", "file.txt"])

    def test_repo_example(self):
        file_names = ["almalinux-ha.repo", "almalinux-powertools.repo", "almalinux-rt.repo",
                      "ELevate.repo", "epel-testing-modular.repo", "imunify360-testing.repo",
                      "kolab-16-testing-candidate.repo", "plesk-ext-ruby.repo", "almalinux-nfv.repo",
                      "almalinux.repo", "almalinux-saphana.repo", "epel-modular.repo",
                      "epel-testing.repo", "imunify-rollout.repo", "kolab-16-testing.repo",
                      "plesk.repo", "almalinux-plus.repo", "almalinux-resilientstorage.repo",
                      "almalinux-sap.repo", "epel.repo", "imunify360.repo",
                      "kolab-16.repo", "plesk-ext-panel-migrator.repo",
                      ]

        for file_name in file_names:
            with open(os.path.join(self.temp_dir, file_name), "w") as f:
                f.write("")

        result = sorted(files.find_files_case_insensitive(self.temp_dir, ["plesk*.repo"]))
        self.assertEqual([os.path.basename(file) for file in result], ["plesk-ext-panel-migrator.repo", "plesk-ext-ruby.repo", "plesk.repo"])