import re
from typing import Optional

from tree_sitter import Node

from ai_gateway.code_suggestions.processing.ops import LanguageId
from ai_gateway.prompts.parsers.base import BaseVisitor
from ai_gateway.prompts.parsers.mixins import RubyParserMixin

__all__ = [
    "BaseDynamicallyLoadedURLVisitor",
    "DynamicallyLoadedURLVisitorFactory",
]

_YAML_LANGUAGE_SERVER_SCHEMA_REF_PATTERN = re.compile(r"# yaml-language-server: \$schema=(?P<schema_url>.*)")

class BaseDynamicallyLoadedURLVisitor(BaseVisitor):
    def __init__(self) -> None:
        self._urls = []

    @property
    def urls(self) -> list[str]:
        return self._urls

class JSONDynamicallyLoadedURLVisitor(BaseDynamicallyLoadedURLVisitor):
    def _visit_node(self, node: Node):
        key = node.children[0]
        if key.text == b'"$schema"':
            value = node.children[2]
            if value.type == "string":
                url = self._bytes_to_str(value.text)
                self._urls = self._urls + [url]

    def visit(self, node: Node):
        # Visit key-value pairs:
        if node.type == "pair":
            # Always visit nodes for now.
            self._visit_node(node)

class YAMLDynamicallyLoadedURLVisitor(BaseDynamicallyLoadedURLVisitor):
    def _visit_node(self, node: Node):
        modeline = _YAML_LANGUAGE_SERVER_SCHEMA_REF_PATTERN.match(self._bytes_to_str(node.text))
        if modeline:
            self._urls = self._urls + [modeline.group("schema_url")]

    def visit(self, node: Node):
        if node.type == "comment":
            self._visit_node(node)

class DynamicallyLoadedURLVisitorFactory:
    _LANG_ID_VISITORS = {
        LanguageId.JSON: JSONDynamicallyLoadedURLVisitor,
        LanguageId.YAML: YAMLDynamicallyLoadedURLVisitor,
    }

    @staticmethod
    def from_language_id(lang_id: LanguageId) -> Optional[BaseDynamicallyLoadedURLVisitor]:
        if klass := DynamicallyLoadedURLVisitorFactory._LANG_ID_VISITORS.get(
            lang_id, None
        ):
            return klass()

        return None
