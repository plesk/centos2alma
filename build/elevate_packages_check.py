#!/usr/bin/env python3
import requests
import argparse

from packaging import version
from bs4 import BeautifulSoup

# Current packages list
current_packages = {
    "leapp": "0.18.0-1",
    "python2-leapp": "0.18.0-1",
    "leapp-data-almalinux": "0.4-5",
    "leapp-deps": "0.18.0-1",
    "leapp-upgrade-el7toel8": "0.21.0-2",
    "leapp-upgrade-el7toel8-deps": "0.21.0-2",
}


def split_name_version(pkg):
    splitted_pkg = pkg.split("-")
    iter = 0
    for part in splitted_pkg:
        if part[0].isdigit():
            break
        iter += 1

    return "-".join(splitted_pkg[:iter]), "-".join(splitted_pkg[iter:])


def retrieve_newer_packages():
    url = 'https://repo.almalinux.org/elevate/el7/aarch64/Packages/'
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    fetched_packages = [a.text.rsplit('.noarch', 1)[0].rsplit('.el7', 1)[0] for a in soup.find_all('a') if a.text.endswith('.rpm')]

    newer_packages = []
    for fetched_pkg in fetched_packages:
        fetched_name, fetched_ver = split_name_version(fetched_pkg)
        # Replace '-' with '.' to make version.parse work. We should do it for both fetched and current versions
        fetched_ver = version.parse(fetched_ver.replace('-', '.'))
        # We need to check only packages that we install directly in the LeapInstallation action. So skip the rest
        if fetched_name in current_packages and fetched_ver > version.parse(current_packages[fetched_name].replace('-', '.')):
            newer_packages.append(fetched_pkg)

    return newer_packages


GITHUB_ISSUE_TITLE = "Newer elevate packages available"


def notify_by_github(newer_packages, github_token, github_repository):
    from github import Github
    g = Github(github_token)
    repo = g.get_repo(github_repository)

    existing_issues = repo.get_issues(state='open')
    for issue in existing_issues:
        if issue.title == GITHUB_ISSUE_TITLE:
            issue.create_comment("The following packages have newer versions available:\n- " + "\n- ".join(newer_packages))
            return

    issue_body = "The following packages have newer versions available:\n- " + "\n- ".join(newer_packages)
    repo.create_issue(title=GITHUB_ISSUE_TITLE, body=issue_body)


def get_known_versions_package_list_from_github_issue(github_token, github_repository):
    issue_packages_map = {}

    from github import Github
    g = Github(github_token)
    repo = g.get_repo(github_repository)
    existing_issues = repo.get_issues(state='open')

    for issue in existing_issues:
        if issue.title == GITHUB_ISSUE_TITLE:
            issue_packages_list = issue.body.split("\n- ")[1:]
            for pkg in issue_packages_list:
                if pkg.startswith("- "):
                    pkg = pkg[2:]
                name, ver = split_name_version(pkg)
                issue_packages_map[name] = ver

            for comment in issue.get_comments():
                issue_packages_list = comment.body.split("\n- ")[1:]
                for pkg in issue_packages_list:
                    if pkg.startswith("- "):
                        pkg = pkg[2:]
                    name, ver = split_name_version(pkg)
                    issue_packages_map[name] = ver
            break

    return issue_packages_map


parser = argparse.ArgumentParser(
    description="Small skript to check for newer elevate packages",
)
parser.add_argument("--github-token", default=None, help="GitHub token to create an issue")
parser.add_argument("--github-repository", default=None, help="GitHub repository to create an issue")
options, extra_args = parser.parse_known_args()

if options.github_token and options.github_repository:
    # If we already have the issue, we should check the known versions from the issue as well
    known_versions = get_known_versions_package_list_from_github_issue(options.github_token, options.github_repository)
    current_packages.update(known_versions)

# Create GitHub issue if there are newer packages
newer_packages = retrieve_newer_packages()
if newer_packages:
    print('Newer packages found:', newer_packages)

    if options.github_token and options.github_repository:
        notify_by_github(newer_packages, options.github_token, options.github_repository)
