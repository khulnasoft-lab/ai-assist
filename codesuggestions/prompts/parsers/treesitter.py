import os
from typing import Optional

from tree_sitter import Language, Node, Parser, Tree

from codesuggestions.prompts.parsers.base import BaseCodeParser, BaseVisitor
from codesuggestions.prompts.parsers.context_extractors import ContextVisitorFactory
from codesuggestions.prompts.parsers.counters import CounterVisitorFactory
from codesuggestions.prompts.parsers.function_signatures import (
    FunctionSignatureVisitorFactory,
)
from codesuggestions.prompts.parsers.imports import ImportVisitorFactory
from codesuggestions.prompts.parsers.treetraversal import tree_dfs
from codesuggestions.suggestions.processing.ops import LanguageId


class CodeParser(BaseCodeParser):
    LANG_ID_TO_LANGUAGE = {
        LanguageId.C: "c",
        LanguageId.CPP: "cpp",
        LanguageId.CSHARP: "c_sharp",
        LanguageId.GO: "go",
        LanguageId.JAVA: "java",
        LanguageId.JS: "javascript",
        LanguageId.PHP: "php",
        LanguageId.PYTHON: "python",
        LanguageId.RUBY: "ruby",
        LanguageId.RUST: "rust",
        LanguageId.SCALA: "scala",
        LanguageId.TS: "typescript",
    }

    def __init__(self, tree: Tree, lang_id: LanguageId):
        self.tree = tree
        self.lang_id = lang_id

    def imports(self) -> list[str]:
        visitor = ImportVisitorFactory.from_language_id(self.lang_id)
        if visitor is None:
            return []

        self._visit_nodes(visitor)
        imports = visitor.imports

        return imports

    def function_signatures(self) -> list[str]:
        visitor = FunctionSignatureVisitorFactory.from_language_id(self.lang_id)
        if visitor is None:
            return []

        self._visit_nodes(visitor)
        function_signatures = visitor.function_signatures

        return function_signatures

    def count_symbols(self) -> dict:
        visitor = CounterVisitorFactory.from_language_id(self.lang_id)
        if visitor is None:
            return []

        self._visit_nodes(visitor)
        counts = visitor.counts

        return counts

    def context_near_cursor(self, point: tuple[int, int]) -> Node:
        visitor = ContextVisitorFactory.from_language_id(self.lang_id, point)
        if visitor is None:
            return None

        self._visit_nodes(visitor)

        node = visitor.extract_most_relevant_context()
        if not node:
            # not able to extract any meaningful context,
            # fallback to using the root node
            return self.tree.root_node
        return node

    def suffix_near_cursor(self, point: tuple[int, int]) -> str:
        context_node = self.context_near_cursor(point)
        _, truncated_suffix = self._split_node(context_node, point)
        return truncated_suffix

    def _split_on_point(self, source_code: str, target_point: tuple[int, int]):
        pos = self._point_to_position(source_code, target_point)
        prefix = source_code[:pos]
        suffix = source_code[pos:]
        return (prefix, suffix)

    def _split_node(self, node: Node, point: tuple[int, int]):
        point_in_node = self._convert_target_point_to_point_in_node(node, point)
        return self._split_on_point(
            node.text.decode("utf-8", errors="ignore"), point_in_node
        )

    def _convert_target_point_to_point_in_node(
        self, node: Node, target_point: tuple[int, int]
    ):
        # translate target_point to point_in_node
        row_in_node = target_point[0] - node.start_point[0]
        col_in_node = target_point[1] - node.start_point[1]
        point_in_node = (row_in_node, col_in_node)
        return point_in_node

    def _point_to_position(self, source_code: str, target_point: tuple[int, int]):
        row, col = target_point
        lines = source_code.splitlines()

        if row >= len(lines) or col > len(lines[row]):
            raise ValueError("Invalid target_point")

        pos = 0
        for i in range(row):
            pos += len(lines[i]) + 1
        pos += col
        return pos

    def _visit_nodes(self, visitor: BaseVisitor):
        tree_dfs(self.tree, visitor)

    @classmethod
    def from_language_id(
        cls,
        content: str,
        lang_id: LanguageId,
        lib_path: Optional[str] = None,
    ):
        if lib_path is None:
            lib_path = "%s/tree-sitter-languages.so" % os.getenv("LIB_DIR", "/usr/lib")

        lang_def = cls.LANG_ID_TO_LANGUAGE.get(lang_id, None)
        if lang_def is None:
            raise ValueError(f"Unsupported language: {lang_id}")

        try:
            parser = Parser()
            parser.set_language(Language(lib_path, lang_def))
            tree = parser.parse(bytes(content, "utf8"))
        except TypeError as ex:
            raise ValueError(f"Unsupported code content: {str(ex)}")

        return cls(tree, lang_id)
