import os
from typing import Annotated
import structlog
from fastapi import APIRouter, Depends, Request
from starlette.authentication import requires

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.autodev.typing import AutodevRequest, AutodevResponse
from ai_gateway.api.v1.autodev.anthropic_client import AnthropicClient
from ai_gateway.api.v1.autodev.tools import (
    fetch_issue,
    clone_repo,
    read_file
)

from ai_gateway.models import (
    AnthropicAPIConnectionError,
    AnthropicAPIStatusError
)
from ai_gateway.tracking.errors import log_exception

import autogen
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent

import tempfile
import os

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("autodev")

router = APIRouter()

CODE_ASSISTANT_SYSTEM_PROMPT="""
You are an automated engineer.
You work with GitLab.
Your job is to create complete code solving 
task described with GitLab issue.
You first analyse issue details and repository source code.
Thne you create implementation plan in natural language.
Once you create implementation plan you write {lang} code according to your plan
When you write complete code that solves the plan you
write 'TERMINATE'
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
    anthropic_llm_config =     {
        # Choose your model name.
        "model": "claude-3-sonnet-20240229",
        # You need to provide your API key here.
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "base_url": "https://api.anthropic.com",
        "api_type": "anthropic",
        "model_client_cls": "AnthropicClient",
    }

    assistant = ConversableAgent(name="assistant", 
                               system_message=CODE_ASSISTANT_SYSTEM_PROMPT.format(lang="ruby"), 
                               llm_config=anthropic_llm_config,
                                max_consecutive_auto_reply=15,
                               )


    user_proxy = ConversableAgent(
        "user_proxy",
        human_input_mode="NEVER", 
        code_execution_config=False, #={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        max_consecutive_auto_reply=15,
    )

    completion: str
    with tempfile.TemporaryDirectory() as work_dir:
        def workdir() -> Annotated[str, "A workdir's path to clone git repositories into"]:
            return work_dir        
     
        # Register the tool signature with the assistant agent.
        assistant.register_for_llm(name="get_workdir", description="A method to get a url of current working directory to use")(workdir)
        assistant.register_for_llm(name="gitlab_issue_fetch", description="An GitLab API wrapper that fetches issue details")(fetch_issue)
        assistant.register_for_llm(name="gitlab_clone_repo", description="A Git source conteroll version wrapper that clone repository to working directory")(clone_repo)
        assistant.register_for_llm(name="read_file", description="A tool that reads file from git repository")(read_file)

        # Register the tool function with the user proxy agent.
        user_proxy.register_for_execution(name="get_workdir")(workdir)
        user_proxy.register_for_execution(name="gitlab_issue_fetch")(fetch_issue)
        user_proxy.register_for_execution(name="gitlab_clone_repo")(clone_repo)
        user_proxy.register_for_execution(name="read_file")(read_file)

        assistant.register_model_client(model_client_cls=AnthropicClient)

        result = user_proxy.initiate_chat(
            assistant,
            message=f"Please implement issue with id {payload.issue_id} in project with id {payload.project_id} from gitlab instance with url {payload.instance_url}",
        )
        completion=result.summary

    return AutodevResponse(response=completion)