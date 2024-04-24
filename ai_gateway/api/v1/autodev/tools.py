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
    headers = {"Private-Token": os.getenv("GDK_SERVICE_ACCOUNT_PAT", "")}
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

# generate method that creates GitLab merge request using API call

def create_merge_request(
    base_url: Annotated[str, "Gitlab instance http URL"],
    project_id: Annotated[int, "Id of the GitLab project"],
    source_branch: Annotated[str, "The name of GitLab branch to use as source for Merge Request"],
    title: Annotated[str, "Title for a Merge Request"],
    description: Annotated[str, "Merge Request description"],
):
    url = f"{base_url}/api/v4/projects/{project_id}/merge_requests"
    headers = {"Private-Token": os.getenv("GDK_SERVICE_ACCOUNT_PAT", "")}
    data = {
        "source_branch": source_branch,
        "target_branch": "master",
        "title": title,
        "description": description,
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log_exception(e)
        raise e


def clone_repo(
    base_url: Annotated[str, "Gitlab instance http URL"],
    project_full_path: Annotated[str, "Issue's project full path"],
    working_directory: Annotated[
        str, "Url of current working directory to clone repo into"
    ],
)->Annotated[
    str,
    "Url of the clonned git repository",
]:
    repo_url = f"{base_url}/{project_full_path}.git"
    try:
        repo = Repo.clone_from(repo_url, working_directory, allow_unsafe_protocols=True)
        repo.git.fetch("origin", "master")
        repo.git.checkout("master")
        return repo.working_dir
    except git.exc.GitCommandError as e:
        log_exception(e)
        return f"Failed to clone repository with error message: {e}"


def read_file(
    working_directory: Annotated[
        str, "Url of current working directory with git repository"
    ],
    file_path: Annotated[str, "A file ulr relative to working directory with git repository"],
) -> Annotated[str, "File content as string"]:
    full_name = os.path.join(working_directory, file_path)
    try:
        with open(full_name, 'r') as f:
            return f.read()
    except FileNotFoundError as e:
        return f"File: {file_path} does not exist in the reposity {working_directory}"
    except IsADirectoryError:
        return f"File: {file_path} is a directory in the reposity {working_directory} it contains {os.listdir(full_name)}"

def write_file(    
    working_directory: Annotated[
        str, "Url of current working directory with git repository"
    ],
    file_path: Annotated[str, "A file ulr relative to working directory with git repository"],
    content: Annotated[str, "File content as string"]
) -> Annotated[str, "File content as string"]:
    full_name = os.path.join(working_directory, file_path)
    with open(full_name, 'w') as f:
        return f.write(content) 

def commit_and_push(
    working_directory: Annotated[
        str, "Url of current working directory with git repository"
    ],
    commit_message: Annotated[str, "Commit message"],
    target_branch: Annotated[str, "Target branch name"],
) -> Annotated[str, "Commit and push status message"]:
        repo = Repo(working_directory)
        repo.git.checkout("-b", target_branch)
        repo.git.add(".")
        repo.git.commit("-m", commit_message)
        repo.git.push("origin", target_branch)
        return f"Commited and pushed to {target_branch} branch"