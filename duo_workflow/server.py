import grpc
import logging
from concurrent.futures import ThreadPoolExecutor
from contract_pb2 import ClientCapabilities, ServerCapabilities
from contract_pb2_grpc import DuoWorkflowServicer, add_DuoWorkflowServicer_to_server
import asyncio

class Workflow:
    # Class that is given a queue on initialize and has a method to check if anything is in the queue
    def __init__(self, queue):
        self.queue = queue

    async def run(self):
        # HACK: Just an example of getting something from the queue
        in_queue = await self.queue.get()
        logging.info("Got something from the queue: %s", in_queue)

class Service(DuoWorkflowServicer):
    # TODO: Why doesn't async def work here?
    async def StartWorkflow(
        self,
        request: ClientCapabilities,
        context: grpc.aio.ServicerContext,
    ) -> ServerCapabilities:
        q = asyncio.Queue()
        w = Workflow(queue=q)

        running =  w.run()

        # HACK: Just an example of putting something in the queue
        await q.put("ABC123")

        await running

        logging.info("Received request with request %s and context %s from peer %s", request, context, context.peer())
        return ServerCapabilities(serverVersion='0.0.1')

async def serve(address: str) -> None:
    server = grpc.aio.server()
    add_DuoWorkflowServicer_to_server(Service(), server)
    server.add_insecure_port(address)
    logging.info("Server serving at %s", address)
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve("[::]:5555"))
