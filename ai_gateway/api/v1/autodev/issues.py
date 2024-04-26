import inspect
import os
from typing import Annotated
import structlog
from fastapi import APIRouter, Depends, Request
from starlette.authentication import requires

from ai_gateway.api.feature_category import feature_category
from ai_gateway.api.v1.autodev.typing import AutodevRequest, AutodevResponse
from ai_gateway.api.v1.autodev.anthropic_client import AnthropicClient
from ai_gateway.api.v1.autodev.tools import (
    commit_and_push,
    create_merge_request,
    fetch_issue,
    clone_repo,
    read_file,
    write_file,
)

from ai_gateway.models import AnthropicAPIConnectionError, AnthropicAPIStatusError
from ai_gateway.tracking.errors import log_exception

import autogen
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent, register_function, GroupChat, GroupChatManager

import tempfile
import os
import functools

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("autodev")

router = APIRouter()

TERMINATE_COMMAND="""
Once you completed all your tasks you must write 'TERMINATE'
"""

CODE_ASSISTANT_SYSTEM_PROMPT = """
You are an automated engineer.
Your job is to follow implementation plan provided by software architect.
You write {lang} code according to the implementation plan
"""

GITLAB_READER_SYSTEM_PROMPT = """
You are a GitLab expert. 
Your task is to use GitLab API
in order to get necessary information from it.
Your task is to use GitLab API to make changes on GitLab instance
"""

GITLAB_WRITER_SYSTEM_PROMPT = """
You are a GitLab expert. 
Your task is to use GitLab API to make changes on GitLab instance
"""

CODE_ARCHITECT_SYSTEM_PROMPT = """
You are an automated {lang} software architect. 
Your task is to break down a complex problem into 
actionable implementation plan that instruct software developers
onto code changes that should be made to the source code.
You are going to receive issue description in natural language
and you will have access to the existing source code. You should review 
issue and source code and write implementation plan in natural language.
"""

@router.post("/issues", response_model=AutodevResponse)
# @requires("code_suggestions")
# @feature_category("code_suggestions")
async def issues(
    request: Request,
    payload: AutodevRequest,
):

    local_llm_config={
        "config_list": [
            {
                "model": "NotRequired", # Loaded with LiteLLM command
                "api_key": "NotRequired", # Not needed
                "base_url": "http://0.0.0.0:4000"  # Your LiteLLM URL
            }
        ],
        "cache_seed": None # Turns off caching, useful for testing different models
    }

    anthropic_llm_config = local_llm_config
    tool_executor: ConversableAgent

    def is_terminating(message):
        return message.get("content", "") and message.get("content", "").rstrip().endswith("TERMINATE")

    human_admin = ConversableAgent(
        "user_proxy",
        description="I am a proxy for the user.",
        human_input_mode="NEVER",
        code_execution_config=False,  # ={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
        is_termination_msg=is_terminating,
        max_consecutive_auto_reply=150,
    )

    gl_reader_agent = ConversableAgent(
        name="gl_reader_agent",
        system_message=GITLAB_READER_SYSTEM_PROMPT + TERMINATE_COMMAND,
        llm_config=anthropic_llm_config,
        max_consecutive_auto_reply=150,
        human_input_mode="NEVER",
    )

    gl_reader_tool_exec = ConversableAgent(
        name="GitLab_Reader_Agent_Tool_Executor",
        human_input_mode="NEVER",
        llm_config=False,
        is_termination_msg=is_terminating
    )
    
    gl_reader_tool_exec.register_nested_chats(
        [
            {
                "recipient":  gl_reader_agent,
                "summary_method": "last_msg",
            }
        ],
        trigger=human_admin
    )

    gl_writer_agent = ConversableAgent(
        name="gl_writer_agent",
        system_message=GITLAB_WRITER_SYSTEM_PROMPT + TERMINATE_COMMAND,
        llm_config=anthropic_llm_config,
        max_consecutive_auto_reply=150,
        human_input_mode="NEVER",
    )

    gl_writer_tool_exec = ConversableAgent(
        name="GitLab_Writer_Agent_Tool_Executor",
        human_input_mode="NEVER",
        llm_config=False,
        is_termination_msg=is_terminating
    )
    
    gl_writer_tool_exec.register_nested_chats(
        [
            {
                "recipient":  gl_writer_agent,
                "summary_method": "last_msg",
            }
        ],
        trigger=human_admin
    )


    architect_agent = ConversableAgent(
        name="architect_agent",
        system_message=CODE_ARCHITECT_SYSTEM_PROMPT.format(lang="ruby") + TERMINATE_COMMAND,
        llm_config=anthropic_llm_config,
        max_consecutive_auto_reply=150,
        human_input_mode="NEVER",
    )

    architec_tool_exec = UserProxyAgent(
        name="Architect_Tool_Executor",
        human_input_mode="NEVER",
        is_termination_msg=is_terminating,
    )

    architec_tool_exec.register_nested_chats(
        [
            {
                "recipient": architect_agent,
                "summary_method": "last_msg",
            }
        ],
        trigger=human_admin
    )

    developer_agent = ConversableAgent(
        name="Developer Agent",
        system_message=CODE_ASSISTANT_SYSTEM_PROMPT.format(lang="ruby") + TERMINATE_COMMAND,
        llm_config=local_llm_config,
        max_consecutive_auto_reply=150,
        human_input_mode="NEVER",
    )

    developer_agent_tool_exec = UserProxyAgent(
        name="Developer_Tool_Executor",
        human_input_mode="NEVER",
        is_termination_msg=is_terminating,
    )

    developer_agent_tool_exec.register_nested_chats(
        [
            {
                "recipient": developer_agent,
                "summary_method": "last_msg",
            }
        ],
        trigger=human_admin
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
        gl_reader_agent.register_for_llm(
            name="gitlab_issue_fetch",
            description="An GitLab API wrapper that fetches issue details",
        )(fetch_issue)
        gl_reader_agent.register_for_llm(
            name="gitlab_clone_repo",
            description="""
            A Git source conteroll version wrapper that clone repository to working directory. 
            Once cloned it returns path to the repository. The repository is checked out to the main branch.
            You can then use repository url to read and write files to it.
            """,
        )(set_workdir(clone_repo))

        for agent in [architect_agent, developer_agent]:
            agent.register_for_llm(
                name="read_file", description="A tool that reads file from git repository"
            )(set_workdir(read_file))

        # Register the tool function with the user proxy agent.
        gl_reader_tool_exec.register_for_execution(name="gitlab_issue_fetch")(fetch_issue)
        gl_reader_tool_exec.register_for_execution(name="gitlab_clone_repo")(set_workdir(clone_repo))
        architec_tool_exec.register_for_execution(name="read_file")(set_workdir(read_file))
        developer_agent_tool_exec.register_for_execution(name="read_file")(set_workdir(read_file))
    
        register_function(
            set_workdir(write_file),
            caller=developer_agent,
            executor=developer_agent_tool_exec,
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
            caller=gl_writer_agent,
            executor=gl_writer_tool_exec,
            name="commit_and_push",
            description="""
            Create a branch with specified name, add files, commit and push the changes to the repository.
            The branch name and commit_message should be descriptive and should contain information about
            the fix as well as the issue number. Please run this after all code has already been written.
            """,
        )

        register_function(
            create_merge_request,
            caller=gl_writer_agent,
            executor=gl_writer_tool_exec,
            name="create_merge_request",
            description="""
            Create GitLab Merge Request from branch with specified name.
            Please run this as the last step after all code has been pushed to the branch
            """,
        )

        result = human_admin.initiate_chats(
            [
                {
                    "recipient": gl_reader_tool_exec, #gl_reader_tool_exec,
                    "summary_method": "last_msg",
                    "max_turns": 1,    
                    "message": f"""
                    Please fetch all issue information issue with id  {payload.issue_id} 
                    in project with id {payload.project_id} from gitlab instance with url {payload.instance_url} and clone project repository.
                    Once you fetched issue details and cloned repository summarise all information into a single message titled with 'Assignement details:'
                    """
                }
                ,{
                    "recipient": architec_tool_exec,
                    "summary_method": "last_msg",
                    "max_turns": 1,    
                    "message": f"""
                    With provided information please create implementation plan for issue with id  {payload.issue_id}
                    Once you formluated the implemetation plan repeat it with title 'Implementation Plan:' and write 'TERMINATE'
                    """
                }
                ,{
                    "recipient": developer_agent_tool_exec,
                    "summary_method": "last_msg",
                    "max_turns": 1,    
                    "message": f"""
                    With provided information follow directly the implementation plan for issue with id  {payload.issue_id}
                    Once you completed following implemetation plan write 'Implementation is completed. TERMINATE'
                    """
                }
                ,{
                    "recipient": gl_writer_tool_exec, #gl_tool_exec,
                    "summary_method": "last_msg",
                    "max_turns": 1,    
                    "message": f"""
                    Implementation of the issue with id  {payload.issue_id} 
                    in project with id {payload.project_id} from gitlab instance with url {payload.instance_url} 
                    is completed now. Please follow steps listed below:
                    1. Create new branch and push it onto GitLab instance.
                    2. Create Merge Request from the branch.
                    3. Write: changes has been pushed and MR has been created thuss 'TERMINATE'    
                    """
                }
            ]
        )

        completion = result.summary

    return AutodevResponse(response=completion)