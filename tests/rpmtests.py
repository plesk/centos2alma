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

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3: id == "repo1"])

        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_multiple_repos(self):
        expected_content = """[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3: id == "repo1",
                                                      lambda id, _1, _2, _3: id == "repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_all_repos(self):
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3: id == "repo1",
                                                      lambda id, _1, _2, _3: id == "repo2",
                                                      lambda id, _1, _2, _3: id == "repo3"])
        self.assertEqual(os.path.exists(self.REPO_FILE_NAME), False)

    def test_remove_non_existing_repo(self):
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3: id == "repo4"])
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

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, _2, _3: id == "repo3"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_with_metalink(self):
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

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""
        additional_repo = """[metarepo]
name=metarepo
metalink=http://metarepo
enabled=1
gpgcheck=0
"""
        with open(self.REPO_FILE_NAME, "a") as f:
            f.write(additional_repo)

        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda _1, _2, _3, metalink: metalink == "http://metarepo"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_with_specific_name(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda _1, name, _2, _3: name == "repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_with_specific_baseurl(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo3]
name=repo3
baseurl=http://repo3
enabled=1
gpgcheck=0
"""
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda _1, _2, baseurl, _3: baseurl == "http://repo2"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    def test_remove_repo_by_id_or_url(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

"""
        rpm.remove_repositories(self.REPO_FILE_NAME, [lambda id, _1, baseurl, _3: id == "repo2" or baseurl == "http://repo3"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)


class WriteRepodataTests(unittest.TestCase):
    REPO_FILE_CONTENT = """[repo1]
name=repo1
baseurl=http://repo1
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

    def test_write_repodata(self):
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
        rpm.write_repodata(self.REPO_FILE_NAME, "repo2", "repo2", "http://repo2", None, ["enabled=1\n", "gpgcheck=0\n"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)

    # Yeah, we don't check if reposiory is already in file. Maybe we will add the check in the future.
    def test_write_exsisted_repodata(self):
        expected_content = """[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0

[repo1]
name=repo1
baseurl=http://repo1
enabled=1
gpgcheck=0
"""
        rpm.write_repodata(self.REPO_FILE_NAME, "repo1", "repo1", "http://repo1", None, ["enabled=1\n", "gpgcheck=0\n"])
        with open(self.REPO_FILE_NAME) as file:
            self.assertEqual(file.read(), expected_content)


class HandleRpmnewFilesTests(unittest.TestCase):
    def test_no_rpmnew(self):
        with open("test.txt", "w") as f:
            f.write("test")

        self.assertFalse(rpm.handle_rpmnew_files("test.txt"))

    def test_has_rpmnew(self):
        with open("test.txt", "w") as f:
            f.write("1")

        with open("test.txt.rpmnew", "w") as f:
            f.write("2")

        self.assertTrue(rpm.handle_rpmnew_files("test.txt"))
        self.assertTrue(os.path.exists("test.txt"))
        self.assertEqual(open("test.txt").read(), "2")

        self.assertTrue(os.path.exists("test.txt.rpmsave"))
        self.assertEqual(open("test.txt.rpmnew").read(), "1")

    def test_missing_original(self):
        with open("test.txt.rpmnew", "w") as f:
            f.write("2")

        self.assertTrue(rpm.handle_rpmnew_files("test.txt"))
        self.assertTrue(os.path.exists("test.txt"))
        self.assertEqual(open("test.txt").read(), "2")

        self.assertFalse(os.path.exists("test.txt.rpmsave"))
