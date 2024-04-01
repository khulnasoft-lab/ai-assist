import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from os import path
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pkg_resources
from pygments.lexers import ClassNotFound, guess_lexer_for_filename
from pygments.token import Token

from ai_gateway.prompts.parsers import CodeParser


@dataclass(slots=True)
class Tag:
    rel_filepath: str
    filepath: str
    line: int
    name: str
    kind: str
    end_line: int
    grammar: str


# This class is responsible for building tags for a given file
# It uses tree-sitter to parse the file and extract tags
# We're using pygments to backfill references for languages that only provide definitions


class TagsBuilder:
    def __init__(
        self,
        executor: ThreadPoolExecutor,
    ):
        self.scm_cache: Dict[str, str] = {}
        self.executor = executor

    async def get_tags_for_file(self, filepath: str, project_root_path: str) -> List[Tag]:
        try:
            relative_filepath = self.get_relative_filepath(filepath, project_root_path)
            file_content = await asyncio.get_running_loop().run_in_executor(
                self.executor, self._read_file, filepath
            )
            if not file_content:
                return []
            code_parser = await CodeParser.from_filename(file_content, filepath)

            # Load the tags queries from cache
            query_scm = await self._get_scm_file(code_parser.grammar)
            if not query_scm:
                return []

            # Run the tags queries
            query = code_parser.tree_sitter_language.query(query_scm)
            captures = query.captures(code_parser.tree.root_node)

            tags: List[Tag] = []
            saw = set()
            for node, tag in captures:
                if tag.startswith("name.definition."):
                    kind = "def"
                elif tag.startswith("name.reference."):
                    kind = "ref"
                else:
                    continue

                saw.add(kind)

                tags.append(
                    Tag(
                        rel_filepath=relative_filepath,
                        filepath=filepath,
                        name=node.text.decode("utf-8"),
                        kind=kind,
                        line=node.start_point[0],
                        end_line=node.end_point[0],
                        grammar=code_parser.grammar,
                    )
                )

            if "ref" in saw:
                return tags
            if "def" not in saw:
                return tags

            try:
                lexer = guess_lexer_for_filename(filepath, file_content)
            except ClassNotFound:
                return tags

            tokens = list(lexer.get_tokens(file_content))
            tokens = [token[1] for token in tokens if token[0] in Token.Name]

            for token in tokens:
                tags.append(
                    Tag(
                        rel_filepath=relative_filepath,
                        filepath=filepath,
                        name=token,
                        kind="ref",
                        line=-1,
                        end_line=-1,
                        grammar=code_parser.grammar,
                    )
                )

            return tags
        except Exception as e:
            print(f"Error in get_tags_for_file: {e}")
            return []

    def _read_file(self, filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    async def _get_scm_file(self, lang: str) -> Optional[str]:
        if lang in self.scm_cache:
            return self.scm_cache[lang]

        try:
            scm_filepath = pkg_resources.resource_filename(
                __name__, path.join("queries", f"tree-sitter-{lang}-tags.scm")
            )
        except KeyError:
            return None

        query_scm = Path(scm_filepath)
        if not query_scm.exists():
            return None

        query_scm_content = await asyncio.get_running_loop().run_in_executor(
            self.executor, query_scm.read_text
        )
        self.scm_cache[lang] = query_scm_content
        return query_scm_content

    def get_relative_filepath(self, filepath: str, rootPath) -> str:
        return path.relpath(filepath, rootPath)
