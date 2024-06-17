import grpc
import logging
from concurrent.futures import ThreadPoolExecutor
from contract_pb2 import ClientCapabilities, ServerCapabilities, ToolResponseAck
from contract_pb2_grpc import DuoWorkflowServicer, add_DuoWorkflowServicer_to_server
import asyncio

class Workflow:
    # Class that is given a queue on initialize and has a method to check if anything is in the queue
    def __init__(self, queue):
        self.queue = queue

    async def run(self):
        logging.info("Running workflow %s and waiting for message", self)
        asyncio.create_task(self.wait_for_queue())

    async def wait_for_queue(self):
        in_queue = await self.queue.get()
        logging.info("Got something for workflow %s from the queue: %s", self, in_queue)


class Service(DuoWorkflowServicer):
    def __init__(self):
        self.queues = {}

    # TODO: Why doesn't async def work here?
    async def StartWorkflow(
        self,
        request: ClientCapabilities,
        context: grpc.aio.ServicerContext,
    ) -> ServerCapabilities:
        q = asyncio.Queue()

        # Track which queue is for which client
        self.queues[context.peer()] = q

        w = Workflow(queue=q)

        await w.run()

        logging.info("Received request with request %s from peer %s", request, context.peer())
        return ServerCapabilities(serverVersion='0.0.1')

    async def ToolResponse(self, request, context):
        q = self.queues[context.peer()]
        await q.put(request)
        return ToolResponseAck()

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
