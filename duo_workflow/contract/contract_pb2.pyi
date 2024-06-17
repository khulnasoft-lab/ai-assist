from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class ClientEvent(_message.Message):
    __slots__ = ("startRequest", "actionResponse")
    STARTREQUEST_FIELD_NUMBER: _ClassVar[int]
    ACTIONRESPONSE_FIELD_NUMBER: _ClassVar[int]
    startRequest: StartWorkflowRequest
    actionResponse: ActionResponse
    def __init__(
        self,
        startRequest: _Optional[_Union[StartWorkflowRequest, _Mapping]] = ...,
        actionResponse: _Optional[_Union[ActionResponse, _Mapping]] = ...,
    ) -> None: ...

class StartWorkflowRequest(_message.Message):
    __slots__ = ("clientVersion", "workflowDefinition", "goal")
    CLIENTVERSION_FIELD_NUMBER: _ClassVar[int]
    WORKFLOWDEFINITION_FIELD_NUMBER: _ClassVar[int]
    GOAL_FIELD_NUMBER: _ClassVar[int]
    clientVersion: str
    workflowDefinition: str
    goal: str
    def __init__(
        self,
        clientVersion: _Optional[str] = ...,
        workflowDefinition: _Optional[str] = ...,
        goal: _Optional[str] = ...,
    ) -> None: ...

class ActionResponse(_message.Message):
    __slots__ = ("requestID", "response")
    REQUESTID_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    requestID: str
    response: str
    def __init__(
        self, requestID: _Optional[str] = ..., response: _Optional[str] = ...
    ) -> None: ...

class Action(_message.Message):
    __slots__ = (
        "requestID",
        "runCommand",
        "runHTTPRequest",
        "runReadFile",
        "runWriteFile",
    )
    REQUESTID_FIELD_NUMBER: _ClassVar[int]
    RUNCOMMAND_FIELD_NUMBER: _ClassVar[int]
    RUNHTTPREQUEST_FIELD_NUMBER: _ClassVar[int]
    RUNREADFILE_FIELD_NUMBER: _ClassVar[int]
    RUNWRITEFILE_FIELD_NUMBER: _ClassVar[int]
    requestID: str
    runCommand: RunCommandAction
    runHTTPRequest: RunHTTPRequest
    runReadFile: ReadFile
    runWriteFile: WriteFile
    def __init__(
        self,
        requestID: _Optional[str] = ...,
        runCommand: _Optional[_Union[RunCommandAction, _Mapping]] = ...,
        runHTTPRequest: _Optional[_Union[RunHTTPRequest, _Mapping]] = ...,
        runReadFile: _Optional[_Union[ReadFile, _Mapping]] = ...,
        runWriteFile: _Optional[_Union[WriteFile, _Mapping]] = ...,
    ) -> None: ...

class RunCommandAction(_message.Message):
    __slots__ = ("command",)
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    command: str
    def __init__(self, command: _Optional[str] = ...) -> None: ...

class ReadFile(_message.Message):
    __slots__ = ("filepath",)
    FILEPATH_FIELD_NUMBER: _ClassVar[int]
    filepath: str
    def __init__(self, filepath: _Optional[str] = ...) -> None: ...

class WriteFile(_message.Message):
    __slots__ = ("filepath", "contents")
    FILEPATH_FIELD_NUMBER: _ClassVar[int]
    CONTENTS_FIELD_NUMBER: _ClassVar[int]
    filepath: str
    contents: str
    def __init__(
        self, filepath: _Optional[str] = ..., contents: _Optional[str] = ...
    ) -> None: ...

class RunHTTPRequest(_message.Message):
    __slots__ = ("method", "path", "body")
    METHOD_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    method: str
    path: str
    body: str
    def __init__(
        self,
        method: _Optional[str] = ...,
        path: _Optional[str] = ...,
        body: _Optional[str] = ...,
    ) -> None: ...
