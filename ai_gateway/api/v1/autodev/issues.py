import inspect
import os
from typing import Annotated
import structlog
from fastapi import APIRouter, Depends, Request
from starlette.authentication import requires

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.autodev.typing import AutodevRequest, AutodevResponse
from ai_gateway.api.v1.autodev.anthropic_client import AnthropicClient
from ai_gateway.api.v1.autodev.tools import commit_and_push, create_merge_request, fetch_issue, clone_repo, read_file, write_file

from ai_gateway.models import AnthropicAPIConnectionError, AnthropicAPIStatusError
from ai_gateway.tracking.errors import log_exception

import autogen
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent, register_function

import tempfile
import os
import functools

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("autodev")

router = APIRouter()

CODE_ASSISTANT_SYSTEM_PROMPT = """
You are an automated engineer.
You work with GitLab.
Your job is to create complete code solving 
task described with GitLab issue.
You first analyse issue details.
Next you create implementation plan in natural language.
Next you review existing source code.
Next you update the implementation plan according to state of the existing source code.
Next you write {lang} code according to the implementation plan
Next you rewrite files with the created code according to the plan.
Next after all actions listed in the implementation plan are completed and the source code 
has been written to correct files you commit and push changes to a new branch. 
Next you create Merge Request from the branch that you pushed code to.
When you created Merge Request you write 'TERMINATE'
"""

# Then you commit changes
# Finally your create Merge Request
# Once Merge Request is created you return 'TERMINATE'


@router.post("/issues", response_model=AutodevResponse)
# @requires("code_suggestions")
# @feature_category("code_suggestions")
async def issues(
    request: Request,
    payload: AutodevRequest,
):
    anthropic_llm_config = {
        # Choose your model name.
        "model": "claude-3-sonnet-20240229",
        # You need to provide your API key here.
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "base_url": "https://api.anthropic.com",
        "api_type": "anthropic",
        "model_client_cls": "AnthropicClient",
    }

    assistant = ConversableAgent(
        name="assistant",
        system_message=CODE_ASSISTANT_SYSTEM_PROMPT.format(lang="ruby"),
        llm_config=anthropic_llm_config,
        max_consecutive_auto_reply=150,
        human_input_mode="NEVER",
    )

    user_proxy = ConversableAgent(
        "user_proxy",
        human_input_mode="NEVER",
        code_execution_config=False,  # ={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
        is_termination_msg=lambda x: x.get("content", "")
        and x.get("content", "").rstrip().endswith("TERMINATE"),
        max_consecutive_auto_reply=150,
    )

    completion: str
    with tempfile.TemporaryDirectory() as work_dir:
        def set_workdir(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                kwargs["working_directory"] = work_dir
                return func(*args, **kwargs)

            return wrapped



        # Register the tool signature with the assistant agent.
        assistant.register_for_llm(
            name="gitlab_issue_fetch",
            description="An GitLab API wrapper that fetches issue details",
        )(fetch_issue)
        assistant.register_for_llm(
            name="gitlab_clone_repo",
            description="""
            A Git source conteroll version wrapper that clone repository to working directory. 
            Once cloned it returns path to the repository. The repository is checked out to the main branch.
            You can then use repository url to read and write files to it.
            """,
        )(set_workdir(clone_repo))
        assistant.register_for_llm(
            name="read_file", description="A tool that reads file from git repository"
        )(set_workdir(read_file))

        # Register the tool function with the user proxy agent.
        user_proxy.register_for_execution(name="gitlab_issue_fetch")(fetch_issue)
        user_proxy.register_for_execution(name="gitlab_clone_repo")(set_workdir(clone_repo))
        user_proxy.register_for_execution(name="read_file")(set_workdir(read_file))

        register_function(
            set_workdir(write_file),
            caller=assistant,
            executor=user_proxy,
            name="write_file",
            description="""
            A tool that writes file to git repository in working directory. 
            Supplied content is going to overwrite existing file fully. 
            If you use this tool to update file, you neeed to pass complete file content to
            rewrite.
            """,
        )

        register_function(
            set_workdir(commit_and_push),
            caller=assistant,
            executor=user_proxy,
            name="commit_and_push",
            description="""
            Create a branch with specified name, add files, commit and push the changes to the repository.
            The branch name and commit_message should be descriptive and should contain information about
            the fix as well as the issue number. Please run this after all code has already been written.
            """,
        )

        register_function(
            create_merge_request,
            caller=assistant,
            executor=user_proxy,
            name="create_merge_request",
            description="""
            Create GitLab Merge Request from branch with specified name.
            Please run this as the last step after all code has been pushed to the branch
            """,
        )

        assistant.register_model_client(model_client_cls=AnthropicClient)

        result = user_proxy.initiate_chat(
            assistant,
            message=f"Please implement issue with id {payload.issue_id} in project with id {payload.project_id} from gitlab instance with url {payload.instance_url}",
        )
        completion = result.summary

    return AutodevResponse(response=completion)
