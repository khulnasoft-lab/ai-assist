# generate async method that given base url of gitlab instance, issue id and project id fetches issue title and description from GitLab API
import os
from pydantic import BaseModel, Field
import structlog
import requests

import git
from git import Repo

from typing import Annotated, Literal
from ai_gateway.tracking.errors import log_exception

log = structlog.stdlib.get_logger("autodev")


class GitLabIssue(BaseModel):
    title: Annotated[str, Field(description="title")]
    description: Annotated[str, Field(description="description")]
    project_full_path: Annotated[str, Field(description="Issue's project full path")]


def fetch_issue(
    base_url: Annotated[str, "Gitlab instance http URL"], issue_id: int, project_id: int
) -> Annotated[
    GitLabIssue,
    "GitLab issue details including title, descrption and issue's project full path",
]:
    url = f"{base_url}/api/v4/projects/{project_id}/issues/{issue_id}"
    headers = {"Private-Token": os.getenv("GITLAB_PRIVATE_TOKEN", "")}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        issue_data = response.json()
        title = issue_data["title"]
        description = issue_data["description"]
        full_path = issue_data["references"]["full"].split("#")[0]
        return GitLabIssue(
            title=title, description=description, project_full_path=full_path
        )
    except requests.exceptions.RequestException as e:
        log_exception(e)
        raise e


# generate method that clones git repository using gitpython
# it should take base_url and full_path as arguments to build https clone path
# it should tak temp_dir argument as output directory


def clone_repo(
    base_url: Annotated[str, "Gitlab instance http URL"],
    project_full_path: Annotated[str, "Issue's project full path"],
    working_directory: Annotated[
        str, "Url of current working directory to clone repo into"
    ],
):  # -> Annotated[Repo, "An instance of Git repository wrapper"]:
    repo_url = f"{base_url}/{project_full_path}.git"
    try:
        repo = Repo.clone_from(repo_url, working_directory, allow_unsafe_protocols=True)
        repo.git.fetch("origin", "master")
        repo.git.checkout("master")
    except git.exc.GitCommandError as e:
        log_exception(e)
        raise e


# generate function that reads file from Repo
def read_file(
    working_directory: Annotated[
        str, "Url of current working directory with git reposito"
    ],
    file_path: Annotated[str, "A file ulr relative to working directory with git repository"],
) -> Annotated[str, "File content as string"]:
    full_name = os.path.join(working_directory, file_path)
    try:
        with open(full_name, 'r') as f:
            return f.read()
    except FileNotFoundError as e:
        return "File {file_path} not found in {working_directory}"
     
    # try:
        # with Repo(path=working_directory) as repo:
        #     with repo.git.rev_parse("HEAD", with_exceptions=True):
        #         blob = repo.tree(repo.head.target)[file_path]
        #         return blob.data_stream.read().decode("utf-8")
    # except git.exc.GitCommandError as e:
    #     log_exception(e)
    #     raise e
