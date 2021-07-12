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



def get_commits(repo, users, reviewers, dir):
    upcoming_changes_path = os.path.join(dir, "doc", "source", "upcoming_changes")
    prs_list = []
    for file in os.listdir(upcoming_changes_path):
        pr_number = file.split(".")[0]
        if (
            os.path.isfile(os.path.join(upcoming_changes_path, file))
            and pr_number.isnumeric()
        ):
            prs_list.append(pr_number)

    if "towncrier_template" in prs_list:
        prs_list.remove("towncrier_template")

    if not prs_list:
        # this list is empty, no significant changes to adress.
        print("No significant changes.")
        return
    else:
        print("Getting all commits from upcoming changes...")

        all_commits = list()
        for pr_number in prs_list:
            try:
                pr = repo.get_pull(int(pr_number))
            except GithubException as e:
                print(str(e))
                continue
            all_commits += [item for item in pr.get_commits()]
            for review in pr.get_reviews():
                if review.user.login not in users:
                    users[review.user.login] = review.user.name
                reviewers.add(users[review.user.login])
        return all_commits


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


def add_to_users(users, new_user):
    if new_user.name is None:
        users[new_user.login] = new_user.login
    else:
        users[new_user.login] = new_user.name


def get_user_args():
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument("pdir", help="Root directory of the scikit-image project.")
    user_args =  parser.parse_args()
    return user_args

def main(user_args=None):
    if not user_args:
        user_args = get_user_args()

    project_dir = user_args.pdir
    GH_USER = "scikit-image"
    GH_REPO = "scikit-image"
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
    repository = g.get_repo(f"{GH_USER}/{GH_REPO}")

    authors = set()
    reviewers = set()
    committers = set()
    users = dict()  # keep track of known usernames

    all_commits = get_commits(repository, users, reviewers, project_dir)

    try:
        # find_author_info(dir, repository)
        for commit in tqdm(all_commits, desc="Getting committers and authors"):
            committer, author = find_author_info(commit)
            if committer is not None:
                committers.add(committer)
                # users maps github ids to a unique name.
                add_to_users(users, commit.committer)
                committers.add(users[commit.committer.login])

            if commit.author is not None:
                add_to_users(users, commit.author)
            authors.add(author)
    except TypeError as e:
        print("No significant changes.")
        filename = Path("reviewers_and_authors.txt")
        filename.write_text("")
        return

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



if __name__ == "__main__":
    main()
