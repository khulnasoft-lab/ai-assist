import asyncio
from typing import List
from gqlalchemy import Memgraph
from ai_gateway.experimentation.ast_poc.tag_builder import TagsBuilder, Tag
from concurrent.futures import ThreadPoolExecutor
from os import unlink, makedirs, path, curdir
import csv


class GraphBuilder:
    def __init__(
        self, memgraph: Memgraph, executor: ThreadPoolExecutor, project_root_path: str
    ):
        self.project_root_path = project_root_path
        self.memgraph = memgraph
        self.tags_builder = TagsBuilder(executor=executor)
        self.executor = executor
        self.processed_files = 0

    async def update_graph_for_file(self, file_path: str, project_root_path: str):
        tags = await self.tags_builder.get_tags_for_file(file_path, project_root_path)
        print(f"Updating graph for {file_path}")

        def_tags = [tag for tag in tags if tag.kind == "def"]
        ref_tags = [tag for tag in tags if tag.kind == "ref"]

        # Batch insert Definer nodes
        self.memgraph.execute(
            "UNWIND $tags AS tag " "MERGE (d:Definer {name: tag.name, file: tag.file})",
            {
                "tags": [
                    {"name": tag.name, "file": tag.rel_filepath} for tag in def_tags
                ]
            },
        )

        # Batch insert Source nodes
        self.memgraph.execute(
            "UNWIND $tags AS tag " "MERGE (s:Source {name: tag.name, file: tag.file})",
            {
                "tags": [
                    {"name": tag.name, "file": tag.rel_filepath} for tag in ref_tags
                ]
            },
        )

        # Batch create REFERENCES relationships
        self.memgraph.execute(
            "UNWIND $tags AS tag "
            "MATCH (s:Source {name: tag.name, file: tag.file}) "
            "MATCH (d:Definer {name: tag.name}) "
            "MERGE (s)-[r:REFERENCES]->(d) "
            "ON CREATE SET r.weight = 1 "
            "ON MATCH SET r.weight = r.weight + 1",
            {
                "tags": [
                    {"name": tag.name, "file": tag.rel_filepath} for tag in ref_tags
                ]
            },
        )

    async def update_graph(self, file_paths: List[str]):
        tasks = []
        for file_path in file_paths:
            task = asyncio.create_task(
                self.update_graph_for_file(
                    file_path=file_path, project_root_path=self.project_root_path
                )
            )
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def query_graph(self, chat_file_paths: List[str]):
        personalization = {}
        for chat_file_path in chat_file_paths:
            rel_fname = self.tags_builder.get_relative_filepath(
                filepath=chat_file_path, rootPath=self.project_root_path
            )
            personalization[rel_fname] = 1.0

        query = """
        CALL pagerank.stream("Source", "REFERENCES", {maxIterations: 100, dampingFactor: 0.85, personalization: $personalization})
        YIELD nodeId, score
        RETURN properties(gds.util.asNode(nodeId)).name AS name, score
        ORDER BY score DESC
        """

        result = self.memgraph.execute_and_fetch(
            query, {"personalization": personalization}
        )
        return result

    async def update_graph_from_csv(self, file_paths: List[str]):
        temp_dir = path.join(path.abspath(curdir), ".tmp")
        makedirs(temp_dir, exist_ok=True)
        temp_csv_path = path.join(temp_dir, "temp.csv")

        num_files = len(file_paths)

        with open(temp_csv_path, mode="w", newline="") as temp_csv:
            csv_writer = csv.writer(temp_csv)
            csv_writer.writerow(["name", "file", "kind"])  #  Header row
            self.processed_files = 0
            tasks = []
            for file_path in file_paths:
                task = asyncio.create_task(
                    self.write_tags_to_csv(file_path=file_path, csv_writer=csv_writer, num_files=num_files)
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

        # Create indexes to speed up the import process
        self.memgraph.execute("CREATE INDEX ON :Definer(name)")
        self.memgraph.execute("CREATE INDEX ON :Source(name)")

        # Load data from CSV into Memgraph
        self.memgraph.execute(
            f"LOAD CSV FROM '/import/temp.csv' WITH HEADER AS row "
            "MERGE (d:Definer {name: row.name, file: row.file}) "
            "WITH d, row WHERE row.kind = 'ref' "
            "MERGE (s:Source {name: row.name, file: row.file}) "
            "MERGE (s)-[r:REFERENCES]->(d) "
            "ON CREATE SET r.weight = 1 "
            "ON MATCH SET r.weight = r.weight + 1"
        )

        # Clean up the temporary CSV file
        unlink(temp_csv.name)

    async def write_tags_to_csv(self, file_path: str, csv_writer, num_files: int):
        tags = await self.tags_builder.get_tags_for_file(
            file_path, self.project_root_path
        )
        for tag in tags:
            csv_writer.writerow([tag.name, tag.rel_filepath, tag.kind])
        self.processed_files += 1
        if self.processed_files % 50 == 0:
          print(
              f"Processed {self.processed_files} files - {self.processed_files/num_files*100}%"
          )
