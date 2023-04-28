import unittest
import os

from common import rpm


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

        rpm.remove_repositories(self.REPO_FILE_NAME, ["repo1"])

        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_multiple_repos(self):
        expected_content = """[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""

        rpm.remove_repositories(self.REPO_FILE_NAME, ["repo1", "repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_all_repos(self):
        rpm.remove_repositories(self.REPO_FILE_NAME, ["repo1", "repo2", "repo3"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.readlines(), [])

    def test_remove_non_existing_repo(self):
        rpm.remove_repositories(self.REPO_FILE_NAME, ["repo4"])
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

        rpm.remove_repositories(self.REPO_FILE_NAME, ["repo3"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)
