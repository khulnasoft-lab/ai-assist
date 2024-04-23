from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Type
import os
import subprocess

class RunCommandInput(BaseModel):
    command: str = Field(description="The command to run")

class RunCommand(BaseTool):
    name = "run_command"
    description = """Run a command in the repository working directory."""
    args_schema: Type[BaseModel] = RunCommandInput

    def _run(self, command: str) -> str:
        # Change to workspace directory while keeping the original working directory
        workspace_name = self.metadata['workspace_name']
        original_dir = os.getcwd()
        os.chdir(workspace_name)

        # Run the command and get both stdout and stderr 
        try:
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout = result.stdout
            stderr = result.stderr
        finally:
            os.chdir(original_dir)

        return {
            "stdout": stdout,
            "stderr": stderr,
        }