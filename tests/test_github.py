import pytest
import logging
import responses
from unittest.mock import patch
from testfixtures import log_capture
from helm_bot.github import (
    add_commit_push,
    add_labels,
    check_fork_exists,
    delete_old_branch,
    checkout_branch,
)


@log_capture()
def test_add_commit_push(capture):
    filename = "filename.txt"
    charts_to_update = ["chart-1", "chart-2"]
    chart_info = {"chart-1": "1.2.3", "chart-2": "4.5.6"}
    repo_name = "test_repo"
    target_branch = "test-branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Adding file: %s" % filename)
    logger.info("Successfully added file: %s" % filename)
    logger.info("Committing file: %s" % filename)
    logger.info("Successfully committed file: %s" % filename)
    logger.info("Pushing commits to branch: %s" % target_branch)
    logger.info("Successfully pushed changes to branch: %s" % target_branch)

    with patch(
        "helm_bot.github.run_cmd",
        return_value={"returncode": 0, "output": "", "err_msg": ""},
    ) as mock_run_cmd:
        add_commit_push(
            filename,
            charts_to_update,
            chart_info,
            repo_name,
            target_branch,
            token,
        )

        assert mock_run_cmd.call_count == 3

        capture.check_present()


@log_capture()
def test_add_commit_push_error(capture):
    filename = "filename.txt"
    charts_to_update = ["chart-1", "chart-2"]
    chart_info = {"chart-1": "1.2.3", "chart-2": "4.5.6"}
    repo_name = "test_repo"
    target_branch = "test-branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Adding file: %s" % filename)
    logger.error("Could not add file: %s" % filename)
    logger.info("Committing file: %s" % filename)
    logger.error("Could not commit file: %s" % filename)
    logger.info("Pushing commits to branch: %s" % target_branch)
    logger.error("Could not push to branch: %s" % target_branch)

    with pytest.raises(RuntimeError):
        add_commit_push(
            filename,
            charts_to_update,
            chart_info,
            repo_name,
            target_branch,
            token,
        )

        capture.check_present()


@log_capture()
def test_add_labels(capture):
    labels = ["label1", "label2"]
    pr_url = "http://jsonplaceholder.typicode.com/issues/1"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Add labels to Pull Request: %s" % pr_url)
    logger.info("Adding labels: %s" % labels)

    with patch("helm_bot.github.post_request") as mocked_func:
        add_labels(labels, pr_url, token)

        assert mocked_func.call_count == 1

        capture.check_present()


@patch(
    "helm_bot.github.get_request",
    return_value=[{"name": "test_repo1"}, {"name": "test_repo2"}],
)
def test_check_fork_exists(mock_args):
    repo_name1 = "test_repo1"
    repo_name2 = "some_other_repo"
    token = "this_is_a_token"

    fork_exists1 = check_fork_exists(repo_name1, token)
    fork_exists2 = check_fork_exists(repo_name2, token)

    assert fork_exists1
    assert not fork_exists2

    assert mock_args.call_count == 2
    mock_args.assert_called_with(
        "https://api.github.com/users/HelmUpgradeBot/repos",
        headers={"Authorization": "token this_is_a_token"},
        json=True,
    )


@responses.activate
@log_capture()
def test_delete_old_branch_does_not_exist(capture):
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Branch does not exist: %s" % target_branch)

    with patch(
        "helm_bot.github.get_request",
        return_value=[{"name": "branch-1"}, {"name": "branch-2"}],
    ) as mocked_func:
        delete_old_branch(repo_name, target_branch, token)

        assert mocked_func.call_count == 1

        capture.check_present()


@responses.activate
@log_capture()
def test_delete_old_branch_does_exist(capture):
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Deleting branch: %s" % target_branch)
    logger.info("Successfully deleted remote branch")
    logger.info("Successfully deleted local branch")

    with patch(
        "helm_bot.github.get_request",
        return_value=[{"name": "branch-1"}, {"name": target_branch}],
    ) as mock_get, patch(
        "helm_bot.github.run_cmd", return_value={"returncode": 0}
    ) as mock_run:
        delete_old_branch(repo_name, target_branch, token)

        assert mock_get.call_count == 1
        assert mock_run.call_count == 2
        capture.check_present()


@log_capture()
def test_checkout_branch_exists(capture):
    repo_owner = "test_owner"
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logger.info("Pulling main branch of: %s/%s" % (repo_owner, repo_name))
    logger.info("Successfully pulled main branch")
    logging.info("Checking out branch: %s" % target_branch)
    logger.info("Successfully checked out branch")

    mock_check_fork = patch(
        "helm_bot.github.check_fork_exists", return_value=True
    )
    mock_delete_branch = patch("helm_bot.github.delete_old_branch")
    mock_run_cmd = patch(
        "helm_bot.github.run_cmd", return_value={"returncode": 0}
    )

    with mock_check_fork as mock1, mock_delete_branch as mock2, mock_run_cmd as mock3:
        checkout_branch(repo_owner, repo_name, target_branch, token)

        assert mock1.call_count == 1
        assert mock2.call_count == 1
        assert mock3.call_count == 2

        capture.check_present()


@log_capture()
def test_checkout_branch_does_not_exist(capture):
    repo_owner = "test_owner"
    repo_name = "test_repo"
    target_branch = "test_branch"
    token = "this_is_a_token"

    logger = logging.getLogger()
    logging.info("Checking out branch: %s" % target_branch)
    logger.info("Successfully checked out branch")

    mock_check_fork = patch(
        "helm_bot.github.check_fork_exists", return_value=False
    )
    mock_run_cmd = patch(
        "helm_bot.github.run_cmd", return_value={"returncode": 0}
    )

    with mock_check_fork as mock1, mock_run_cmd as mock2:
        checkout_branch(repo_owner, repo_name, target_branch, token)

        assert mock1.call_count == 1
        assert mock2.call_count == 1

        capture.check_present()
