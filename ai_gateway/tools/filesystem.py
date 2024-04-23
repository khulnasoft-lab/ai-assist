from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Type
import os

class ReadFileInput(BaseModel):
    file_path: str = Field(description="the file_path to read the file from")

class ReadFile(BaseTool):
    name = "read_file"
    description = """Read the contents of a file."""
    args_schema: Type[BaseModel] = ReadFileInput

    def _run(self, file_path: str) -> str:
        workspace_name = self.metadata['workspace_name']
        try:
            actual_path = os.path.join(workspace_name, file_path)
            with open(actual_path, 'r') as f:
                contents = f.read()
        except Exception as e:
            return f"ERROR: {e}"
        return contents

class WriteFileInput(BaseModel):
    file_path: str = Field(description="the file_path to write the file to")
    contents: str = Field(description="the contents to write in the file")

class WriteFile(BaseTool):
    name = "write_file"
    description = """Write the given contents to a file. Please specify the file_path and the contents to write."""
    args_schema: Type[BaseModel] = WriteFileInput

    def _run(self, file_path: str, contents: str) -> str:
        workspace_name = self.metadata['workspace_name']

        if not(contents):
            return "ERROR: You need to specify the contents of the file."
        try:
            actual_path = os.path.join(workspace_name, file_path)
            with open(actual_path, 'w') as f:
                f.write(contents)
        except Exception as e:
            return f"ERROR: {e}"
        return "SUCCESS"