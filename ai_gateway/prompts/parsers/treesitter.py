import os
from typing import Optional

from tree_sitter import Language, Node, Parser, Tree

from ai_gateway.code_suggestions.processing.ops import (
    LanguageId,
    ProgramLanguage,
    convert_point_to_relative_point_in_node,
    split_on_point,
)
from ai_gateway.prompts.parsers.base import (
    BaseCodeParser,
    BaseVisitor,
    CodeContext,
    Point,
)
from ai_gateway.prompts.parsers.blocks import ErrorBlocksVisitor, MinAllowedBlockVisitor
from ai_gateway.prompts.parsers.comments import CommentVisitorFactory
from ai_gateway.prompts.parsers.context_extractors import ContextVisitorFactory
from ai_gateway.prompts.parsers.counters import CounterVisitorFactory
from ai_gateway.prompts.parsers.function_signatures import (
    FunctionSignatureVisitorFactory,
)
from ai_gateway.prompts.parsers.imports import ImportVisitorFactory
from ai_gateway.prompts.parsers.treetraversal import tree_dfs


class CodeParser(BaseCodeParser):
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

    def suffix_near_cursor(self, point: tuple[int, int]) -> Optional[str]:
        """
        Finds the suffix near the cursor based on language-specific rules.

        Returns None if there are no rules for the language or no relevant context was found.
        """
        node = self._context_near_cursor(point)
        if not node:
            return None

        point_in_node = convert_point_to_relative_point_in_node(node, point)
        _, suffix = split_on_point(
            node.text.decode("utf-8", errors="ignore"), point_in_node
        )
        return suffix

    def _context_near_cursor(self, point: tuple[int, int]) -> Optional[Node]:
        visitor = ContextVisitorFactory.from_language_id(self.lang_id, point)
        if visitor is None:
            return None

        self._visit_nodes(visitor)

        return visitor.extract_most_relevant_context()

    def min_allowed_context(self, point: Point) -> CodeContext:
        visitor = MinAllowedBlockVisitor(point, min_block_size=2)
        if visitor is None:
            return CodeContext.from_node(self.tree.root_node)

        self._visit_nodes(visitor)

        if block_node := visitor.block:
            return CodeContext.from_node(block_node)

        return CodeContext.from_node(self.tree.root_node)

    def errors(self, include_missing=True) -> list[CodeContext]:
        visitor = ErrorBlocksVisitor()
        self._visit_nodes(visitor)

        if include_missing:
            return list(map(CodeContext.from_node, visitor.errors))
        else:
            return list(
                map(
                    CodeContext.from_node,
                    [e for e in visitor.errors if not e.is_missing],
                )
            )

    def _visit_nodes(self, visitor: BaseVisitor):
        tree_dfs(self.tree, visitor)

    def comments_only(self) -> bool:
        visitor = self._comments_visitor()
        if not visitor:
            return False

        return visitor.comments_only

    def ends_with_comment(self) -> bool:
        visitor = self._comments_visitor()
        if not visitor:
            return False

        return visitor.ends_with_comment

    def _comments_visitor(self) -> BaseCommentVisitor:
        visitor = CommentVisitorFactory.from_language_id(self.lang_id)
        if visitor is None:
            return None

        self._visit_nodes(visitor)
        return visitor

    @classmethod
    def from_language_id(
        cls,
        content: str,
        lang_id: LanguageId,
        lib_path: Optional[str] = None,
    ):
        if lib_path is None:
            lib_path = "%s/tree-sitter-languages.so" % os.getenv("LIB_DIR", "/usr/lib")

        if lang_id is None:
            raise ValueError(f"Unsupported language: {lang_id}")

        lang_def = ProgramLanguage.from_language_id(lang_id)

        try:
            parser = Parser()
            parser.set_language(Language(lib_path, lang_def.grammar_name))
            tree = parser.parse(bytes(content, "utf8"))
        except TypeError as ex:
            raise ValueError(f"Unsupported code content: {str(ex)}")

        return cls(tree, lang_id)
