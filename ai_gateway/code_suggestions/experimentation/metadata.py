from langchain.chat_models import ChatAnthropic
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from pydantic import BaseModel, Field

__all__ = ["FileMetadataChainInput", "FileMetadataChainOutput", "file_metadata_chain"]

PROMPT_TEMPLATE_FILE_METADATA = """
As a software engineer, your task is to provide a summary of the code file located at "{file_path}"
and each individual function within the file.

Input format:
```
{{
  "code": "code here"
}}
```

{output_format}

Please ensure that your summary accurately describes the content and purpose of the file
and each individual function within it. The summary should be formatted as valid JSON
and include details such as the language and type of file. Additionally, please provide information
on any library or file imports and function parameters.

Begin!

```
{{
  "code": "{code}"
}}
```
""".strip(
    "\n"
)


class FileMetadataChainInput(BaseModel):
    file_path: str
    code: str


class FileMetadataChainOutput(BaseModel):
    class FunctionEntity(BaseModel):
        class FunctionEntityParameter(BaseModel):
            name: str = Field(description="Name of the parameter")
            description: str = Field(description="Description of the parameter")
            parameter_type: str = Field(description="Type of the parameter")

        function_name: str = Field(description="Name of the function")
        function_description: str = Field(
            description="Description of the function in maximum 5 sentences"
        )
        function_parameters: list[FunctionEntityParameter] = Field(
            description="Function parameters"
        )

    file_summary: str = Field(description="Description of the file content")
    language: str = Field(description="Programming language of the file content")
    library_imports: list[str] = Field(description="Libraries imported")
    file_imports: list[str] = Field(description="file paths imported")
    public_exports: list[str] = Field(
        description="classes, functions and variables exported"
    )
    functions: list[FunctionEntity] = Field(
        description="Detailed description of functions"
    )


def file_metadata_chain(
    model: ChatAnthropic,
) -> Runnable[dict, FileMetadataChainOutput]:
    parser = PydanticOutputParser(pydantic_object=FileMetadataChainOutput)
    prompt = PromptTemplate(
        input_variables=list(FileMetadataChainInput.__fields__.keys()),
        template=PROMPT_TEMPLATE_FILE_METADATA,
        partial_variables={"output_format": parser.get_format_instructions()},
    )

    model.temperature = 0.1

    chain = prompt | model | parser

    return chain
