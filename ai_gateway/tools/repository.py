from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Type
import git

class CloneInput(BaseModel):
    repository_ssh_url: str = Field(description="the ssh url for the repository to clone")

class Clone(BaseTool):
    name = "clone_repository"
    description = "Clone a Git repository. Once the repository is cloned you will automatically be in the repository working directory and the main branch will already be checked out."
    args_schema: Type[BaseModel] = CloneInput

    def _run(self, repository_ssh_url: str) -> str:
        """Use the tool."""
        workspace_name = self.metadata['workspace_name']
        git.Repo.clone_from(repository_ssh_url, workspace_name)
        return "Repository cloned successfully"

class CreateBranchCommitPushInput(BaseModel):
    branch_name: str = Field(description="a branch name specific to the issue. please use best pratices for naming")
    commit_message: str = Field(description="A description commit message describing the change.")

class CreateBranchCommitPush(BaseTool):
    name = "create_branch_commit_and_push"
    description = """Create a branch with specified name, add files, commit and push the changes to the repository.
    The branch name and commit_message should be descriptive and should contain information about
    the fix as well as the issue number. Please run this after the issue is fixed."""
    args_schema: Type[BaseModel] = CreateBranchCommitPushInput

    def _run(self, branch_name: str, commit_message: str) -> str:
        workspace_name = self.metadata['workspace_name']
        repo = git.Repo(workspace_name)
        repo.git.checkout("-b", branch_name)
        repo.git.add(".")
        repo.git.commit("-m", f"'{commit_message}'")
        repo.git.push("origin", branch_name)
        return "SUCCESS"