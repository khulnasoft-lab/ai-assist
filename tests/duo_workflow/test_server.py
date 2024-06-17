from typing import AsyncIterable
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

import duo_workflow.contract.contract_pb2 as contract_pb2
from duo_workflow.server import DuoWorkflowService, serve


@pytest.mark.asyncio
async def test_execute_workflow():
    async def mock_request_iterator() -> AsyncIterable[contract_pb2.ClientEvent]:
        yield contract_pb2.ClientEvent()

    mock_context = MagicMock(spec=grpc.ServicerContext)
    servicer = DuoWorkflowService()
    result = servicer.ExecuteWorkflow(mock_request_iterator(), mock_context)
    assert isinstance(result, AsyncIterable)
    assert isinstance(await result.__anext__(), contract_pb2.Action)


@pytest.mark.asyncio
async def test_serve():
    mock_server = AsyncMock()
    mock_server.add_insecure_port.return_value = None
    mock_server.start.return_value = None
    mock_server.wait_for_termination.return_value = None

    with patch("duo_workflow.server.grpc.aio.server", return_value=mock_server):
        await serve(50052)

    mock_server.add_insecure_port.assert_called_once_with("[::]:50052")
    mock_server.start.assert_called_once()
    mock_server.wait_for_termination.assert_called_once()


if __name__ == "__main__":
    pytest.main()
