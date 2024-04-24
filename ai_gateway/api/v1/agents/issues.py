from fastapi import APIRouter
from pydantic import BaseModel

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic

from unique_names_generator import get_random_name
from unique_names_generator.data import ADJECTIVES, NAMES

from ai_gateway.tools.repository import Clone, CreateBranchCommitPush
from ai_gateway.tools.gitlab import FetchIssue, CreateGitlabMergeRequest
from ai_gateway.tools.filesystem import ReadFile, WriteFile
from ai_gateway.tools.command import RunCommand

import gitlab
import os

router = APIRouter()

class IssueFixerInput(BaseModel):
    project_id: str
    issue_id: str

@router.post("/issue_fixer")
def issue_fixer(input: IssueFixerInput):
    llm = ChatAnthropic(model_name="claude-3-sonnet-20240229")
    gl = gitlab.Gitlab(private_token=os.getenv("GITLAB_TOKEN"))
    
    random_name = get_random_name(
        combo=[ADJECTIVES, NAMES], separator="_", style="lowercase")

    workspace_name = os.path.join("workspaces", random_name)
    metadata = {
        "workspace_name": workspace_name,
        "gitlab": gl
    }
    
    tools = [
        Clone(metadata=metadata), CreateBranchCommitPush(metadata=metadata),
        ReadFile(metadata=metadata), WriteFile(metadata=metadata),
        RunCommand(metadata=metadata),
        FetchIssue(metadata=metadata), CreateGitlabMergeRequest(metadata=metadata)
    ]

    chat_template = ChatPromptTemplate.from_messages(
        [
            ("system", """
            You have the software engineering capabilities of a Principle engineer. 
            You can clone a repository, run commands and make changes to files. 
            Make sure you follow test driven development and write tests to verify the functionality that you are building.
            Please write code in only the language that is specified in the repository.
            Make a plan on what needs to be done. The plan should include
            1. Understand the issue
            2. Clone the repository (please use SSH to clone)
            3. Read code files to verify the issue
            5. Fix issue by writing files
            6. Write tests to confirm that your program works
            7. Push changes to the repository
            8. Create a merge request for the change
             
            Once the plan has been executed your final response should be in markdown format with a summary of what has been completed and a link to the merge request.
            """),
            ("placeholder", "{chat_history}"),
            ("human", "Can you help fix the following issue: {input}."),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=chat_template)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    result = agent_executor.invoke({"input": f"Project ID: {input.project_id} , Issue: {input.issue_id}"})
    return {
        'text': result['output']
    }
