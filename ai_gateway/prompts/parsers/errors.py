from tree_sitter import Node

from ai_gateway.prompts.parsers.base import BaseVisitor

__all__ = ["ErrorVisitor"]


class ErrorVisitor(BaseVisitor):
    def __init__(self):
        self._errors = 0

    def _visit_node(self, node: Node):
        if node.type == "ERROR":
            self._errors += 1

    @property
    def error_count(self) -> int:
        return self._errors

    def visit(self, node: Node):
        # override the inherited method to visit all nodes
        self._visit_node(node)
