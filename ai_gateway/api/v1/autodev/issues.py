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

GITLAB_OPERATOR_SYSTEM_PROMPT = """
You are a GitLab expert. 
Your task is to use GitLab API
in order to get necessary information from it.
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

    assistant = ConversableAgent(
        name="assistant",
        system_message=CODE_ASSISTANT_SYSTEM_PROMPT.format(lang="ruby") + TERMINATE_COMMAND,
        llm_config=local_llm_config,
        max_consecutive_auto_reply=150,
        human_input_mode="NEVER",
    )

    # group_chat = GroupChat(
    #     agents=group_chat_participants,
    #     messages=[],
    #     max_round=60
    # )
    # group_chat_manager = GroupChatManager(
    #     groupchat=group_chat,
    #     llm_config=anthropic_llm_config,
    #     system_message=group_chat.introductions_msg()
    # )

    # gl_operator_agent.register_nested_chats(
    #     trigger=[group_chat_manager, *group_chat_participants],
    #     chat_queue=[
    #         {
                    
    #         }
    #     ]
    # )

    gl_operator_agent = ConversableAgent(
        name="gl_operator_agent",
        system_message=GITLAB_OPERATOR_SYSTEM_PROMPT + TERMINATE_COMMAND,
        llm_config=anthropic_llm_config,
        max_consecutive_auto_reply=150,
        human_input_mode="NEVER",
    )

    gl_tool_exec = ConversableAgent(
        name="GitLab_Agent_Tool_Executor",
        human_input_mode="NEVER",
        llm_config=False,
        is_termination_msg=is_terminating
    )
    
    gl_tool_exec.register_nested_chats(
        [
            {
                "recipient":  gl_operator_agent,
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

    # def reflection_message_architect(recipient, messages, sender, config):
    #     print("Architect Reflecting...", "yellow")
    #     return f". \n\n {recipient.chat_messages_for_summary(sender)[-1]['content']}"



    architec_tool_exec.register_nested_chats(
        [
            {
                "recipient": architect_agent,
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
        gl_operator_agent.register_for_llm(
            name="gitlab_issue_fetch",
            description="An GitLab API wrapper that fetches issue details",
        )(fetch_issue)
        gl_operator_agent.register_for_llm(
            name="gitlab_clone_repo",
            description="""
            A Git source conteroll version wrapper that clone repository to working directory. 
            Once cloned it returns path to the repository. The repository is checked out to the main branch.
            You can then use repository url to read and write files to it.
            """,
        )(set_workdir(clone_repo))

        for agent in [architect_agent, assistant]:
            agent.register_for_llm(
                name="read_file", description="A tool that reads file from git repository"
            )(set_workdir(read_file))

        # Register the tool function with the user proxy agent.
        gl_tool_exec.register_for_execution(name="gitlab_issue_fetch")(fetch_issue)
        gl_tool_exec.register_for_execution(name="gitlab_clone_repo")(set_workdir(clone_repo))
        architec_tool_exec.register_for_execution(name="read_file")(set_workdir(read_file))
    
        result = human_admin.initiate_chats(
            [
                {
                    "recipient": gl_tool_exec, #gl_tool_exec,
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
            ]
        )
        # result = human_admin.initiate_chat(
        #     recipient=gl_tool_exec,
        #     max_turns=1, 
        #     summary_method="last_msg",
        #     message=f"""
        #              Please fetch all issue information issue with id  {payload.issue_id} 
        #              in project with id {payload.project_id} from gitlab instance with url {payload.instance_url} and clone project repository.
        #              Once you fetched issue details and cloned repository summarise all information into a single message titled with 'Assignement details:'
        #              """
        # )
        # result = gl_tool_exec.initiate_chat(
        #     gl_operator_agent,
        #     summary_method="last_msg",
        #     # summary_prompt="Summarize all collected information and write 'TERMINATE'",
        #     message=f"""
        #              Please fetch all issue information issue with id  {payload.issue_id} 
        #              in project with id {payload.project_id} from gitlab instance with url {payload.instance_url} and clone project repository.
        #              Once you fetched issue details and cloned repository summarise all information into a single message titled with 'Assignement details:'
        #              """
        # )
        breakpoint()
        completion = result.summary

    return AutodevResponse(response=completion)
        # register_function(
        #     set_workdir(write_file),
        #     caller=assistant,
        #     executor=tool_executor,
        #     name="write_file",
        #     description="""
        #     A tool that writes file to git repository in working directory. 
        #     Supplied content is going to overwrite existing file fully. 
        #     If you use this tool to update file, you neeed to pass complete file content to
        #     rewrite.
        #     """,
        # )

        # register_function(
        #     set_workdir(commit_and_push),
        #     caller=gl_operator_agent,
        #     executor=tool_executor,
        #     name="commit_and_push",
        #     description="""
        #     Create a branch with specified name, add files, commit and push the changes to the repository.
        #     The branch name and commit_message should be descriptive and should contain information about
        #     the fix as well as the issue number. Please run this after all code has already been written.
        #     """,
        # )

        # register_function(
        #     create_merge_request,
        #     caller=gl_operator_agent,
        #     executor=tool_executor,
        #     name="create_merge_request",
        #     description="""
        #     Create GitLab Merge Request from branch with specified name.
        #     Please run this as the last step after all code has been pushed to the branch
        #     """,
        # )

        # for agent in [architect_agent, assistant, gl_operator_agent, group_chat_manager]:
        #     agent.register_model_client(model_client_cls=AnthropicClient)

        # nested_chats = [
        #     {
        #         "recipient": group_chat_manager,
        #         "summary_method": "reflection_with_llm",
        #     },
        #     {
        #         "recipient": code_writer_agent,
        #         "message": "Write a Python script to verify the arithmetic operations is correct.",
        #         "summary_method": "reflection_with_llm",
        #     },
        #     {
        #         "recipient": poetry_agent,
        #         "message": "Write a poem about it.",
        #         "max_turns": 1,
        #         "summary_method": "last_msg",
        #     },
        # ]
        # result = gl_operator_agent.initiate_chat(
        #     group_chat_manager,
        #     message = f"""
        #     Please implement issue with id {payload.issue_id} in project with id {payload.project_id} from gitlab instance with url {payload.instance_url}
        #     Once source code changes are ready commit them to a new branch and create Merge Request
        #     """,
        #     summary_method="reflection_with_llm"
        # )
        # completion = result.summary


