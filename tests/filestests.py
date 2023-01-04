import unittest
import os
import json

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