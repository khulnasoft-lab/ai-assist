import asyncio
from typing import List, Tuple, Dict
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
            "UNWIND $tags AS tag "
            "MERGE (d:Definer {name: tag.name, file: tag.file, line: tag.line, end_line: tag.end_line, grammar: tag.grammar, project_root: $project_root})",
            {
                "tags": [
                    {
                        "name": tag.name,
                        "file": tag.rel_filepath,
                        "line": tag.line,
                        "end_line": tag.end_line,
                        "grammar": tag.grammar,
                    }
                    for tag in def_tags
                ],
                "project_root": project_root_path,
            },
        )

        # Batch insert Source nodes
        self.memgraph.execute(
            "UNWIND $tags AS tag "
            "MERGE (s:Source {name: tag.name, file: tag.file, line: tag.line, end_line: tag.end_line, grammar: tag.grammar, project_root: $project_root})",
            {
                "tags": [
                    {
                        "name": tag.name,
                        "file": tag.rel_filepath,
                        "line": tag.line,
                        "end_line": tag.end_line,
                        "grammar": tag.grammar,
                    }
                    for tag in ref_tags
                ],
                "project_root": project_root_path,
            },
        )

        # Batch create REFERENCES relationships with identifier information
        self.memgraph.execute(
            "UNWIND $tags AS tag "
            "MATCH (s:Source {name: tag.name, file: tag.file, line: tag.line, end_line: tag.end_line, grammar: tag.grammar, project_root: $project_root}) "
            "MATCH (d:Definer {name: tag.name, project_root: $project_root}) "
            "MERGE (s)-[r:REFERENCES {ident: tag.name}]->(d) "
            "ON CREATE SET r.weight = 1 "
            "ON MATCH SET r.weight = r.weight + 1",
            {
                "tags": [
                    {
                        "name": tag.name,
                        "file": tag.rel_filepath,
                        "line": tag.line,
                        "end_line": tag.end_line,
                        "grammar": tag.grammar,
                    }
                    for tag in ref_tags
                ],
                "project_root": project_root_path,
            },
        )


    async def update_graph_from_csv(self, file_paths: List[str]):
        temp_dir = path.join(path.abspath(curdir), ".tmp")
        makedirs(temp_dir, exist_ok=True)
        temp_csv_path = path.join(temp_dir, "temp.csv")

        num_files = len(file_paths)

        with open(temp_csv_path, mode="w", newline="") as temp_csv:
            csv_writer = csv.writer(temp_csv)
            csv_writer.writerow(
                [
                    "name",
                    "file",
                    "kind",
                    "ident",
                    "line",
                    "end_line",
                    "grammar",
                    "project_root",
                ]
            )
            self.processed_files = 0
            tasks = []
            for file_path in file_paths:
                task = asyncio.create_task(
                    self._write_tags_to_csv(
                        file_path=file_path, csv_writer=csv_writer, num_files=num_files
                    )
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

        # Create indexes to speed up the import process
        self.memgraph.execute("CREATE INDEX ON :Definer(name)")
        self.memgraph.execute("CREATE INDEX ON :Source(name)")

        # Load data from CSV into Memgraph
        self.memgraph.execute(
            f"LOAD CSV FROM '/import/temp.csv' WITH HEADER AS row "
            "MERGE (d:Definer {name: row.name, file: row.file, line: toInteger(row.line), end_line: toInteger(row.end_line), grammar: row.grammar, project_root: row.project_root}) "
            "WITH d, row WHERE row.kind = 'ref' "
            "MERGE (s:Source {name: row.name, file: row.file, line: toInteger(row.line), end_line: toInteger(row.end_line), grammar: row.grammar, project_root: row.project_root}) "
            "MERGE (s)-[r:REFERENCES {ident: row.ident}]->(d) "
            "ON CREATE SET r.weight = 1 "
            "ON MATCH SET r.weight = r.weight + 1"
        )

        # Clean up the temporary CSV file
        unlink(temp_csv.name)

    async def _write_tags_to_csv(self, file_path: str, csv_writer, num_files: int):
        tags = await self.tags_builder.get_tags_for_file(
            file_path, self.project_root_path
        )
        for tag in tags:
            csv_writer.writerow(
                [
                    tag.name,
                    tag.rel_filepath,
                    tag.kind,
                    tag.name,
                    tag.line,
                    tag.end_line,
                    tag.grammar,
                    self.project_root_path,
                ]
            )
        self.processed_files += 1
        if self.processed_files % 50 == 0:
            print(
                f"Processed {self.processed_files} files - {self.processed_files/num_files*100}%"
            )


    async def query_graph(self, chat_file_paths: List[str]):
        personalization = {}
        for chat_file_path in chat_file_paths:
            rel_fname = self.tags_builder.get_relative_filepath(
                filepath=chat_file_path, rootPath=self.project_root_path
            )
            personalization[rel_fname] = 1.0

        query = """
        CALL pagerank.stream("Source", "REFERENCES", {maxIterations: 100, dampingFactor: 0.85, weightProperty: "weight", personalization: $personalization})
        YIELD nodeId, score
        MATCH (s:Source {id: nodeId})
        RETURN s.name AS name, s.file AS file, s.line AS line, s.end_line AS end_line, s.grammar AS grammar, s.project_root AS project_root, score
        ORDER BY score DESC
        """

        result = self.memgraph.execute_and_fetch(
            query, {"personalization": personalization}
        )
        return result

    async def get_ranked_tags(
        self, chat_file_paths: List[str], other_file_paths: List[str]
    ) -> List[Tuple[Tag, ...]]:
        ranked_nodes = await self.query_graph(chat_file_paths)
        ranked_definitions = await self.get_ranked_definitions(ranked_nodes)
        ranked_tags = self.create_ranked_tags(ranked_definitions, chat_file_paths)
        ranked_tags = self.include_other_files(ranked_tags, other_file_paths)
        return ranked_tags

    async def get_ranked_definitions(
        self, ranked_nodes: List[Tuple[str, str, int, int, str, float]]
    ) -> Dict[Tuple[str, str], Dict[str, float]]:
        ranked_definitions: Dict[Tuple[str, str], Dict[str, float]] = {}
        for (
            node_name,
            node_file,
            node_line,
            node_end_line,
            node_grammar,
            score,
        ) in ranked_nodes:
            query = """
                MATCH (s:Source {name: $name, file: $file, line: $line, end_line: $end_line, grammar: $grammar})-[r:REFERENCES]->(d:Definer)
                RETURN d.file AS file, d.name AS name, d.line AS line, d.end_line AS end_line, d.grammar AS grammar, r.weight AS weight, r.ident AS ident
            """
            edges = self.memgraph.execute_and_fetch(
                query,
                {
                    "name": node_name,
                    "file": node_file,
                    "line": node_line,
                    "end_line": node_end_line,
                    "grammar": node_grammar,
                },
            )
            for edge in edges:
                file = edge["file"]
                ident = edge["ident"]
                line = edge["line"]
                end_line = edge["end_line"]
                grammar = edge["grammar"]
                weight = edge["weight"]
                key = (file, ident)
                if key not in ranked_definitions:
                    ranked_definitions[key] = {
                        "score": 0.0,
                        "line": line,
                        "end_line": end_line,
                        "grammar": grammar,
                    }
                ranked_definitions[key]["score"] += score * weight
        return ranked_definitions

    def create_ranked_tags(
        self,
        ranked_definitions: Dict[Tuple[str, str], Dict[str, float]],
        chat_file_paths: List[str],
    ) -> List[Tuple[Tag, ...]]:
        ranked_tags: List[Tuple[Tag, ...]] = []
        for (file, ident), data in sorted(
            ranked_definitions.items(), key=lambda x: x[1]["score"], reverse=True
        ):
            if file in chat_file_paths:
                continue
            tag = Tag(
                file,
                self.project_root_path + file,
                data["line"],
                ident,
                "def",
                data["end_line"],
                data["grammar"],
            )
            ranked_tags.append((tag,))
        return ranked_tags

    def include_other_files(
        self, ranked_tags: List[Tuple[Tag, ...]], other_file_paths: List[str]
    ) -> List[Tuple[Tag, ...]]:
        rel_other_file_paths_without_tags = set(
            self.tags_builder.get_relative_filepath(
                filepath=file_path, rootPath=self.project_root_path
            )
            for file_path in other_file_paths
        )
        file_paths_already_included = set(rt[0].rel_filepath for rt in ranked_tags)

        for file in rel_other_file_paths_without_tags:
            if file not in file_paths_already_included:
                tag = Tag(file, self.project_root_path + file, -1, "", "def", -1, "")
                ranked_tags.append((tag,))

        return ranked_tags
