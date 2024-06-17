import asyncio
import logging
import os
from typing import AsyncIterable

import grpc

from duo_workflow.contract import contract_pb2, contract_pb2_grpc


class DuoWorkflowService(contract_pb2_grpc.DuoWorkflowServicer):
    # pylint: disable=invalid-overridden-method
    async def ExecuteWorkflow(
        self,
        request_iterator: AsyncIterable[contract_pb2.ClientEvent],
        context: grpc.ServicerContext,
    ) -> AsyncIterable[contract_pb2.Action]:
        # Fetch the start workflow call
        start_workflow_request = await anext(aiter(request_iterator))
        logging.info("Starting workflow %s", start_workflow_request)
        # TODO: Connect this to autograph
        yield contract_pb2.Action(
            runCommand=contract_pb2.RunCommandAction(command="ls")
        )

    # pylint: enable=invalid-overridden-method


async def serve(port: int) -> None:
    server = grpc.aio.server()
    contract_pb2_grpc.add_DuoWorkflowServicer_to_server(DuoWorkflowService(), server)
    server.add_insecure_port(f"[::]:{port}")
    logging.info("Starting server on port %d", port)
    await server.start()
    logging.info("Started server")
    await server.wait_for_termination()


def run():
    logging.basicConfig(level=logging.INFO)
    # pylint: disable=direct-environment-variable-reference
    port = int(os.environ.get("PORT", "50052"))
    # pylint: enable=direct-environment-variable-reference
    asyncio.get_event_loop().run_until_complete(serve(port))


if __name__ == "__main__":
    run()
