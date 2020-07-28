import os
import shutil
import logging

from itertools import compress

from .helper_functions import (
    delete_request,
    get_request,
    post_request,
    run_cmd,
)

logger = logging.getLogger()


def check_versions(
    chart_name: str, chart_info: dict, dry_run: bool = False
) -> list:
    charts = list(chart_info.keys())
    charts.remove(deployment)

    condition = [
        (
            chart_info[chart]["version"]
            != chart_info[chart_name][chart]["version"]
        )
        for chart in charts
    ]
    charts_to_update = list(compress(charts, condition))

    if condition.any() and (not dry_run):
        logger.info(
            "Helm upgrade required for the following charts: %s"
            % charts_to_update
        )
    elif condition.any() and dry_run:
        logger.info(
            "Helm upgrade required for the following charts: %s. PR won't be opened due to --dry-run flag being set."
            % charts_to_update
        )
    else:
        logger.info(
            "%s is up-to-date with all current chart dependency releases!"
            % chart_name
        )

    return charts_to_update


def clean_up(repo_name: str) -> None:
    cwd = os.getcwd()
    this_dir = cwd.split("/")[-1]
    if this_dir == repo_name:
        os.chdir(os.pardir)

    if os.path.exists(repo_name):
        logger.info("Deleting local repository: %s" % repo_name)
        shutil.rmtree(repo_name)
        logger.info("Deleted local repository: %s" % repo_name)


def get_chart_versions(chart_name: str, repo_owner: str, repo_name: str):
    chart_info = {}
    chart_urls = {
        chart_name: f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/main/{chart_name}/requirements.yaml",
        "binderhub": "https://raw.githubusercontent.com/jupyterhub/helm-chart/gh-pages/index.yaml",
        "nginx-ingress": "https://raw.githubusercontent.com/helm/charts/master/stable/nginx-ingress/Chart.yaml",
    }

    for (chart, chart_url) in chart_urls.items():
        if "requirements.yaml" in chart_url:
            # Get the versions from a requirements.yaml file
            pass
        elif "Chart.yaml" in chart_url:
            # Get the versions from a Chart.yaml file
            pass
        elif "/gh-pages/" in chart_url:
            # Get the versions from a gh-pages page
            pass
        else:
            msg = "Scraping from the following URL type is currently not implemented\n\t%s" % chart_url
            logger.error(NotImplementedError(msg))
            raise NotImplementedError(msg)

    return chart_info
