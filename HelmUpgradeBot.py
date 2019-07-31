"""
Script to pull the latest Helm Chart deployment from:
https://jupyterhub.github.io/helm-chart/#development-releases-binderhub
and compare the latest release with the Hub23 changelog.

If Hub23 needs an upgrade, the script will perform the upgrade and open a pull
request documenting the new helm chart version in the changelog.
"""

import os
import sys
import stat
import time
import shutil
import logging
import datetime
import requests
import subprocess
import pandas as pd
from yaml import safe_load as load

# Hub23 repo API URL
REPO_API = "https://api.github.com/repos/alan-turing-institute/hub23-deploy/"

# Access token for GitHub API
TOKEN = os.environ.get("BOT_TOKEN")

# Setup logging config
logging.basicConfig(
    level=logging.DEBUG,
    filename="HelmUpgradeBot.log",
    filemode="a",
    format="[%(asctime)s %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def get_latest_versions():
    """Get latest Helm Chart versions

    Returns
    -------
    version_info
        Dictionary.
    """
    version_info = {"hub23": {}, "helm_page": {}}

    logging.info("Fetching the latest Helm Chart version deployed on Hub23")
    changelog_url = "https://raw.githubusercontent.com/alan-turing-institute/hub23-deploy/master/changelog.txt"
    changelog = load(requests.get(changelog_url).text)
    version_info["hub23"]["date"] = pd.to_datetime(list(changelog.keys())[-1])
    version_info["hub23"]["version"] = changelog[list(changelog.keys())[-1]]

    url_helm_chart = "https://raw.githubusercontent.com/jupyterhub/helm-chart/gh-pages/index.yaml"
    logging.info(f"Fetching the latest Helm Chart version from: {url_helm_chart}")
    helm_chart_yaml = load(requests.get(url_helm_chart).text)
    updates_sorted = sorted(
        helm_chart_yaml["entries"]["binderhub"],
        key=lambda k: k["created"]
    )
    version_info["helm_page"]["date"] = updates_sorted[-1]['created']
    version_info["helm_page"]["version"] = updates_sorted[-1]['version']

    logging.info(f"Hub23: {version_info['hub23']['date']} {version_info['hub23']['version']}")
    logging.info(f"Helm Chart page: {version_info['helm_page']['date']} {version_info['helm_page']['version']}")

    return version_info

def check_fork_exists():
    """Check if fork exists

    Returns
    -------
    fork_exists
        Boolean.
    """
    res = requests.get("https://api.github.com/users/HelmUpgradeBot/repos")
    fork_exists = bool([x for x in res.json() if x["name"] == "hub23-deploy"])

    return fork_exists

def remove_fork():
    """Remove fork

    Returns
    -------
    fork_exists
        Boolean.
    """
    fork_exists = check_fork_exists()

    if fork_exists:
        logging.info("HelmUpgradeBot has a fork of hub23-deploy")
        requests.delete(
            "https://api.github.com/repos/HelmUpgradeBot/hub23-deploy/",
            headers={"Authorization": f"token {TOKEN}"}
        )
        fork_exists = False
        time.sleep(5)
        logging.info("Fork deleted")

    else:
        logging.info("HelmUpgradeBot does not have a fork of hub23-deploy")
        return fork_exists

def clone_fork():
    """Clone fork"""
    logging.info("Cloning fork")
    proc = subprocess.Popen(
        ["git", "clone", "https://github.com/HelmUpgradeBot/hub23-deploy.git"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    res = proc.communicate()
    if proc.returncode == 0:
        logging.info("Fork successfully cloned")
    else:
        err_msg = res[1].decode(encoding="utf-8")
        logging.error(err_msg)

def make_fork():
    """Create a fork

    Returns
    -------
    fork_exists
        Boolean.
    """
    logging.info("Creating fork of hub23-deploy")
    requests.post(
        REPO_API + "forks",
        headers={"Authorization": f"token {TOKEN}"}
    )
    fork_exists = True
    logging.info("Fork created")

    return fork_exists

def set_github_config():
    subprocess.check_call([
        "git", "config", "user.name", "HelmUpgradeBot"
    ])
    subprocess.check_call([
        "git", "config", "user.email", "helmupgradebot.github@gmail.com"
    ])

def delete_old_branch():
    """Delete old git branch"""
    logging.info("Deleting branch: helm_chart_bump")
    req = requests.get(
        "https://api.github.com/repos/HelmUpgradeBot/hub23-deploy/branches"
    )

    if "helm_chart_bump" in [x["name"] for x in req.json()]:
        proc = subprocess.Popen(
            ["git", "push", "--delete", "origin", "helm_chart_bump"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info("Successfully deleted remote branch: helm_chart_bump")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        proc = subprocess.Popen(
            ["git", "branch", "-d", "helm_chart_bump"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info("Successfully deleted local branch: helm_chart_bump")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

def checkout_branch(fork_exists):
    """Checkout a git branch

    Parameters
    ----------
    fork_exists
        Boolean
    """
    if fork_exists:
        delete_old_branch()

        logging.info("Pulling master branch")
        proc = subprocess.Popen(
            [
                "git", "pull",
                "https://github.com/alan-turing-institute/hub23-deploy.git",
                "master"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        proc.communicate()
        if proc.returncode == 0:
            logging.info("Successfully pulled master branch")
        else:
            err_msg = res[1].decode(Encoding="utf-8")
            logging.error(err_msg)

    logging.info("Checking out branch: helm_chart_bump")
    proc = subprocess.Popen(
        ["git", "checkout", "-b", "helm_chart_bump"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    res = proc.communicate()
    if proc.returncode == 0:
        logging.info("Successfully checked out branch: helm_chart_bump")
    else:
        err_msg = res[1].decode(encoding="utf-8")
        logging.error(err_msg)

def update_changelog(version_info):
    """Update changelog file

    Parameters
    ----------
    version_info
        Dictionary.

    Returns
    -------
    fname
        List of strings. Filenames of changed files.
    """
    fname = "changelog.txt"
    logging.info(f"Updating files: {fname}")

    with open(fname, "a") as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {version_info['helm_page']['version']}")

    logging.info(f"Updated file: {fname}")

    return [fname]

def add_commit_push(changed_files, version_info):
    """Add commit and push files

    Parameters
    ----------
    changed_files
        List of strings. Filenames to process.
    version_info
        Dictionary.
    """
    for f in changed_files:
        logging.info(f"Adding file: {f}")
        proc = subprocess.Popen(
            ["git", "add", f],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully added file: {f}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        commit_msg = f"Log Helm Chart bump to version {version_info['helm_page']['version']}"

        logging.info(f"Committing file: {f}")
        proc = subprocess.Popen(
            ["git", "commit", "-m", commit_msg],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Successfully committed file: {f}")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        logging.info("Pushing commits to branch: helm_chart_bump")
        proc = subprocess.Popen(
            [
                "git", "push",
                f"https://HelmUpgradeBot:{TOKEN}@github.com/HelmUpgradeBot/hub23-deploy",
                "helm_chart_bump"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info("Successfully pushed changes to branch: helm_chart_bump")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

def make_pr_body(version_info):
    """Make PR body

    Parameters
    ----------
    version_info
        Dictionary.

    Returns
    -------
    body
        String.
    """
    logging.info("Writing Pull Request body")

    today = pd.Timestamp.now().tz_localize(None)
    body = "\n".join([
        "This PR is updating the CHANGELOG to reflect the most recent Helm Chart version bump.",
        f"It had been {(today - version_info['hub23']['date']).days} days since the last upgrade."
    ])

    logging.info("Pull Request body written")

    return body

def create_update_pr(version_info):
    """Create a PR

    Parameters
    ----------
    version_info
        Dictionary.
    """
    logging.info("Creating a Pull Request")

    body = make_pr_body(version_info)

    pr = {
        "title": "Logging Helm Chart version upgrade",
        "body": body,
        "base": "master",
        "head": "HelmUpgradeBot:helm_chart_bump"
    }

    requests.post(
        REPO_API + "pulls",
        headers={"Authorization": f"token {TOKEN}"},
        json=pr
    )

    logging.info("Pull Request created")

def clean_up():
    cwd = os.getcwd()
    this_dir = cwd.split("/")[-1]
    if this_dir == "hub23-deploy":
        os.chdir(os.pardir)

    logging.info("Deleting local repository: hub23-deploy")
    shutil.rmtree(this_dir)
    logging.info("Deleted local repository: hub23-deploy")

def main():
    version_info = get_latest_versions()
    fork_exists = remove_fork()
    set_github_config()

    date_cond = (version_info["helm_page"]["date"] > version_info["hub23"]["date"])
    version_cond = (version_info["helm_page"]["version"] != version_info["hub23"]["version"])

    if date_cond and version_cond:
        logging.info("Helm upgrade required")

        # Forking repo
        if not fork_exists:
            fork_exists = make_fork()
        clone_fork()
        os.chdir("hub23-deploy")

        # Make shell scripts executable
        os.chmod("make-config-files.sh", 0o700)
        os.chmod("upgrade.sh", 0o700)

        # Generating config files
        logging.info("Generating Hub23 configuration files")
        proc = subprocess.Popen(
            ["./make-config-files.sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info("Successfully generated configuration files")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        # Upgrading Helm Chart
        logging.info("Upgrading Hub23 Helm Chart")
        proc = subprocess.Popen(
            ["./upgrade.sh", version_info["helm_page"]["version"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        res = proc.communicate()
        if proc.returncode == 0:
            logging.info("Successfully upgraded Hub23 Helm Chart")
        else:
            err_msg = res[1].decode(encoding="utf-8")
            logging.error(err_msg)

        checkout_branch(fork_exists)
        fname = update_changelog(version_info)
        add_commit_push(fname, version_info)
        create_update_pr(version_info)

    else:
        logging.info("Hub23 is up-to-date with current BinderHub Helm Chart release!")

        today = pd.Timestamp.now().tz_localize(None)

        if ((today - version_info["helm_page"]["date"]).days >= 7) and fork_exists:
            fork_exists = remove_fork()

    clean_up()

if __name__ == "__main__":
    main()
