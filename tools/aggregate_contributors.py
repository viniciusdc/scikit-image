import os
import argparse
from datetime import datetime
from collections import OrderedDict
import string
from pathlib import Path
from warnings import warn

from github import Github
from github import GithubException

try:
    from tqdm import tqdm
except ImportError:
    from warnings import warn

    warn(
        "tqdm not installed. This script takes approximately 5 minutes "
        "to run. To view live progressbars, please install tqdm. "
        "Otherwise, be patient."
    )

    def tqdm(i, **kwargs):
        return i


def get_prs_list(upcoming_changes_path):
    prs_list = []
    for file in os.listdir(upcoming_changes_path):
        pr_number = file.split(".")[0]
        if (
            os.path.isfile(os.path.join(upcoming_changes_path, file))
            and pr_number.isnumeric()
        ):
            prs_list.append(int(pr_number))
    return prs_list


def get_remote():
    GH_TOKEN = os.environ.get("GH_TOKEN")
    if GH_TOKEN is None:
        raise RuntimeError(
            "It is necessary that the environment variable `GH_TOKEN` "
            "be set to avoid running into problems with rate limiting. "
            "One can be acquired at https://github.com/settings/tokens.\n\n"
            "You do not need to select any permission boxes while generating "
            "the token."
        )

    g = Github(GH_TOKEN)
    remote = g.get_repo(f"scikit-image/scikit-image")
    return remote


def get_prs_info(project_dir):
    all_commits = []
    upcoming_changes_path = os.path.join(
        project_dir, "doc", "source", "upcoming_changes"
    )
    remote = get_remote()
    prs_list = get_prs_list(upcoming_changes_path)
    reviews = []
    print("Getting all commits from upcoming changes...")
    for pr_number in prs_list:
        try:
            pr = remote.get_pull(pr_number)
        except GithubException as e:
            print(str(e))
            continue
        all_commits += [item for item in pr.get_commits()]
        reviews += [r for r in pr.get_reviews()]
    return all_commits, reviews


def find_author_info(commit):
    """Return committer and author of a commit.

    Parameters
    ----------
    commit : Github commit
        The commit to query.

    Returns
    -------
    committer : str or None
        The git committer.
    author : str
        The git author.
    """
    committer = None
    if commit.committer is not None:
        committer = commit.committer.name or commit.committer.login
    git_author = commit.raw_data["commit"]["author"]["name"]
    if commit.author is not None:
        author = commit.author.name or commit.author.login + f" ({git_author})"
    else:
        # Users that deleted their accounts will appear as None
        author = git_author
    return committer, author


def get_contributor_info(all_commits, reviews):
    authors = set()
    committers = set()

    for commit in tqdm(all_commits, desc="Getting committers and authors"):
        committer, author = find_author_info(commit)
        if committer is not None:
            committers.add(committer)
        authors.add(author)
    reviewers = {r.user.login for r in reviews}
    return authors, committers, reviewers


def add_to_users(users, new_user):
    if new_user.name is None:
        users[new_user.login] = new_user.login
    else:
        users[new_user.login] = new_user.name


def save_contributors_info(authors, committers, reviewers):

    # this gets found as a commiter
    committers.discard("GitHub Web Flow")
    authors.discard("Azure Pipelines Bot")

    contributors = OrderedDict()

    contributors["authors"] = authors
    # contributors['committers'] = committers
    contributors["reviewers"] = reviewers
    with open("reviewers_and_authors.txt", "w+") as file:
        for section_name, contributor_set in contributors.items():
            file.write("\n")
            committer_str = (
                f"{len(contributor_set)} {section_name} added to this "
                "release [alphabetical by first name or login]\n"
            )
            file.write(committer_str)
            file.write("-" * len(committer_str))
            file.write("\n")

            # Remove None from contributor set if it's in there.
            if None in contributor_set:
                contributor_set.remove(None)

            for c in sorted(contributor_set, key=str.lower):
                file.write(f"- {c} \n")
            file.write("\n")


def get_user_args():
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument("pdir", help="Root directory of the scikit-image project.")
    user_args = parser.parse_args()
    return user_args


def main(user_args=None):
    if not user_args:
        user_args = get_user_args()

    project_dir = user_args.pdir
    all_commits, reviews = get_prs_info(project_dir)

    authors, committers, reviewers = get_contributor_info(all_commits, reviews)

    save_contributors_info(authors, committers, reviewers)


if __name__ == "__main__":
    main()
