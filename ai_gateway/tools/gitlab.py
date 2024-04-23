from langchain.tools import BaseTool
from gitlab.v4.objects import Issue, MergeRequest
from langchain.pydantic_v1 import BaseModel, Field
from typing import Type

class FetchIssueInput(BaseModel):
    project_id: str = Field(description="the project_id of the GitLab project")
    issue_id: str = Field(description="the issue_id")

class FetchIssue(BaseTool):
    name = "fetch_issue"
    description = "Fetch an issue from a GitLab project."
    args_schema: Type[BaseModel] = FetchIssueInput

    def _run(self, project_id: str, issue_id: str) -> Issue:
        gl = self.metadata['gitlab']
        project = gl.projects.get(project_id)
        issue = project.issues.get(issue_id)
        return issue

class CreateGitlabMergeRequestInput(BaseModel):
    project_id: str = Field(description="the project_id of the GitLab project")
    branch: str = Field(description="the branch to create the merge request from")
    title: str = Field(description="Title of the merge request")
    description: str = Field(description="detailed description of the merge request")

class CreateGitlabMergeRequest(BaseTool):
    name = "create_gitlab_merge_request"
    description = "Create a merge request on GitLab."
    args_schema: Type[BaseModel] = CreateGitlabMergeRequestInput

    def _run(self, project_id: str, branch: str, title: str, description: str) -> MergeRequest:
        gl = self.metadata['gitlab']
        project = gl.projects.get(project_id)
        merge_request = project.mergerequests.create({
            "source_branch": branch,
            "target_branch": "main",
            "title": title,
            "description": description,
        })
        return merge_request
