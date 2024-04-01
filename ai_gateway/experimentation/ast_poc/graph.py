import asyncio
from typing import List
from gqlalchemy import Memgraph
from ai_gateway.experimentation.ast_poc.tag_builder import TagsBuilder
from concurrent.futures import ThreadPoolExecutor

class GraphBuilder:
    def __init__(self, memgraph: Memgraph, executor: ThreadPoolExecutor, project_root_path: str):
        self.project_root_path = project_root_path
        self.memgraph = memgraph
        self.tags_builder = TagsBuilder(executor=executor)
        self.executor = executor  

    async def update_graph_for_file(self, file_path: str, project_root_path: str):
        tags = await self.tags_builder.get_tags_for_file(file_path, project_root_path)
        print(f"Updating graph for {file_path}", self.memgraph.execute)
        for tag in tags:
            if tag.kind == "def":
                self.memgraph.execute(
                    "MERGE (d:Definer {name: $name, file: $file})",
                    {"name": tag.name, "file": tag.rel_filepath},
                )

            if tag.kind == "ref":
                self.memgraph.execute(
                    "MERGE (s:Source {name: $name, file: $file})",
                    {"name": tag.name, "file": tag.rel_filepath},
                )

                self.memgraph.execute(
                    """
                    MATCH (s:Source {name: $name, file: $file})
                    MATCH (d:Definer {name: $name})
                    MERGE (s)-[r:REFERENCES]->(d)
                    ON CREATE SET r.weight = 1
                    ON MATCH SET r.weight = r.weight + 1
                    """,
                    {"name": tag.name, "file": tag.rel_filepath},
                )


    async def update_graph(self, file_paths: List[str]):
        tasks = []
        for file_path in file_paths:
            task = asyncio.create_task(self.update_graph_for_file(file_path=file_path, project_root_path=self.project_root_path))
            tasks.append(task)

        await asyncio.gather(*tasks)

    async def query_graph(self, chat_file_paths: List[str]):
        personalization = {}
        for chat_file_path in chat_file_paths:
            rel_fname = self.tags_builder.get_relative_filepath(filepath=chat_file_path, rootPath=self.project_root_path)
            personalization[rel_fname] = 1.0

        query = """
            CALL pagerank.stream("Source", "REFERENCES", {maxIterations: 100, dampingFactor: 0.85, personalization: $personalization})
            YIELD nodeId, score
            RETURN properties(gds.util.asNode(nodeId)).name AS name, score
            ORDER BY score DESC
        """
        result = await self.memgraph.execute_and_fetch(query, {"personalization": personalization})
        return result

