#!/usr/bin/env python3
import requests
import argparse

from packaging import version
from bs4 import BeautifulSoup

# Current packages
current_packages = [
    "leapp-0.18.0-1",
    "python2-leapp-0.18.0-1",
    "leapp-data-almalinux-0.4-5",
    "leapp-deps-0.18.0-1",
    "leapp-upgrade-el7toel8-0.21.0-2",
    "leapp-upgrade-el7toel8-deps-0.21.0-2",
]


def retrieve_newer_packages():
    url = 'https://repo.almalinux.org/elevate/el7/aarch64/Packages/'
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    fetched_packages = [a.text for a in soup.find_all('a') if a.text.endswith('.rpm')]

    newer_packages = []
    for current_pkg in current_packages:
        current_name, current_ver = current_pkg.rsplit('-', 1)
        for fetched_pkg in fetched_packages:
            if fetched_pkg.startswith(current_name):
                fetched_ver = fetched_pkg[len(current_name)+1:].rsplit('.el7', 1)[0]
                if version.parse(fetched_ver) > version.parse(current_ver):
                    newer_packages.append(fetched_pkg)
                    break
    return newer_packages


def notify_by_github(newer_packages, github_token, github_repository):
    from github import Github
    g = Github(github_token)
    repo = g.get_repo(github_repository)
    issue_title = "Newer elevate packages available"

    existing_issues = repo.get_issues(state='open')
    for issue in existing_issues:
        if issue.title == issue_title:
            issue.create_comment("The following packages have newer versions available:\n- " + "\n- ".join(newer_packages))
            return

    issue_body = "The following packages have newer versions available:\n- " + "\n- ".join(newer_packages)
    repo.create_issue(title=issue_title, body=issue_body)


parser = argparse.ArgumentParser(
    description="Small skript to check for newer elevate packages",
)
parser.add_argument("--github-token", default=None, help="GitHub token to create an issue")
parser.add_argument("--github-repository", default=None, help="GitHub repository to create an issue")
options, extra_args = parser.parse_known_args()

# Create GitHub issue if there are newer packages
newer_packages = retrieve_newer_packages()
if newer_packages:
    print('Newer packages found:', newer_packages)

    if options.github_token and options.github_repository:
        notify_by_github(newer_packages, options.github_token, options.github_repository)
