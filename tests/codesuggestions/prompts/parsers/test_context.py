import pytest
from tree_sitter import Node

from codesuggestions.prompts.parsers import CodeParser
from codesuggestions.prompts.parsers.context_extractors import BaseContextVisitor
from codesuggestions.prompts.parsers.treetraversal import tree_dfs
from codesuggestions.suggestions.processing.ops import LanguageId

PYTHON_PREFIX_SAMPLE = """
from abc import ABC
from abc import abstractmethod

from tree_sitter import Node


class BaseVisitor(ABC):
    _TARGET_SYMBOL = None

    @abstractmethod
    def _visit_node(self, node: Node):
        pass

    @property
    def stop_earlier(self) -> bool:
        return False

    def visit(self, node: Node):
        # use self instead of the class name to access the overridden attribute
        if self._TARGET_SYMBOL and node.type == self._TARGET_SYMBOL:
            self._visit_node("""

PYTHON_SUFFIX_SAMPLE = """node)


class BaseCodeParser(ABC):
    @abstractmethod
    def count_symbols(self) -> dict:
        pass

    @abstractmethod
    def imports(self) -> list[str]:
        pass

"""

_PYTHON_PREFIX_EXPECTED_FUNCTION_DEFINITION_CONTEXT = """
def visit(self, node: Node):
        # use self instead of the class name to access the overridden attribute
        if self._TARGET_SYMBOL and node.type == self._TARGET_SYMBOL:
            self._visit_node(
"""

_PYTHON_PREFIX_EXPECTED_CLASS_DEFINITION_CONTEXT = """
class BaseVisitor(ABC):
    _TARGET_SYMBOL = None

    @abstractmethod
    def _visit_node(self, node: Node):
        pass

    @property
    def stop_earlier(self) -> bool:
        return False

    def visit(self, node: Node):
        # use self instead of the class name to access the overridden attribute
        if self._TARGET_SYMBOL and node.type == self._TARGET_SYMBOL:
            self._visit_node(
"""


@pytest.mark.parametrize(
    (
        "lang_id",
        "source_code",
        "target_point",
        "expected_node_count",
        "expected_context",
        "priority_list",
    ),
    [
        (
            LanguageId.PYTHON,
            PYTHON_PREFIX_SAMPLE,
            (21, 29),
            8,
            _PYTHON_PREFIX_EXPECTED_FUNCTION_DEFINITION_CONTEXT,
            ["function_definition"],
        ),
        (
            LanguageId.PYTHON,
            PYTHON_PREFIX_SAMPLE,
            (21, 29),
            8,
            _PYTHON_PREFIX_EXPECTED_CLASS_DEFINITION_CONTEXT,
            ["class_definition"],
        ),
        (
            LanguageId.PYTHON,
            PYTHON_PREFIX_SAMPLE + PYTHON_SUFFIX_SAMPLE,
            (21, 29),
            10,
            """def visit(self, node: Node):
        # use self instead of the class name to access the overridden attribute
        if self._TARGET_SYMBOL and node.type == self._TARGET_SYMBOL:
            self._visit_node(node)
""",
            ["function_definition"],
        ),
    ],
)
def test_base_context_visitor(
    lang_id: LanguageId,
    source_code: str,
    target_point: tuple[int, int],
    expected_node_count: int,
    expected_context: str,
    priority_list: list[str],
):
    parser = CodeParser.from_language_id(source_code, lang_id)
    visitor = BaseContextVisitor(target_point)
    tree_dfs(parser.tree, visitor)

    context_node = visitor.extract_most_relevant_context(priority_list=priority_list)
    assert context_node is not None

    actual_context = visitor._bytes_to_str(context_node.text)

    assert len(visitor.visited_nodes) == expected_node_count
    assert actual_context.strip() == expected_context.strip()


PYTHON_SAMPLE_TWO_FUNCTIONS = """
def sum(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""

PYTHON_SAMPLE_FUNCTION_WITHIN_FUNCTION = """
import os

def i_want_to_sum(a, b):
    def sum(a, b):
        return a + b
    return sum(a, b)
"""


@pytest.mark.parametrize(
    (
        "lang_id",
        "source_code",
        "target_point",
        "expected_prefix",
        "expected_suffix",
    ),
    [
        (  # Test context at function level
            LanguageId.PYTHON,
            PYTHON_SAMPLE_TWO_FUNCTIONS[1:],
            (0, 14),
            "def sum(a, b):",
            "\n    return a + b",
        ),
        (  # Test context at function level
            LanguageId.PYTHON,
            PYTHON_SAMPLE_TWO_FUNCTIONS[1:],
            (0, 13),
            "def sum(a, b)",
            ":\n    return a + b",
        ),
        (  # Test context at function level
            LanguageId.PYTHON,
            PYTHON_SAMPLE_TWO_FUNCTIONS[1:],
            (0, 12),
            "def sum(a, b",
            "):\n    return a + b",
        ),
        (  # Test context at function level
            LanguageId.PYTHON,
            PYTHON_SAMPLE_TWO_FUNCTIONS[1:],
            (0, 11),
            "def sum(a, ",
            "b):\n    return a + b",
        ),
        (  # Test context at function level
            LanguageId.PYTHON,
            PYTHON_SAMPLE_FUNCTION_WITHIN_FUNCTION[1:],
            (2, 20),
            'import os\n\ndef i_want_to_sum(a,',
            ' b):\n    def sum(a, b):\n        return a + b\n    return sum(a, b)',
        ),
        (  # Test context at module level
            LanguageId.PYTHON,
            PYTHON_SAMPLE_TWO_FUNCTIONS[1:],
            (2, 0),
            "def sum(a, b):\n    return a + b\n",
            "\ndef subtract(a, b):\n    return a - b\n",
        ),
    ],
)
def test_python_context_visitor(
    lang_id: LanguageId,
    source_code: str,
    target_point: tuple[int, int],
    expected_prefix: str,
    expected_suffix: str,
):
    print()
    print("-----------------------")
    print(f"{target_point=}")
    print("-----------------------")
    print("source_code:")
    print("-----------------------")
    pos = _point_to_position(source_code, target_point)
    print(_highlight_position(pos, source_code))

    # Extract relevant context around the cursor
    parser = CodeParser.from_language_id(source_code, lang_id)
    context_node = parser.context_near_cursor(target_point)
    assert context_node is not None
    print("-----------------------")
    print("context_node:")
    print(context_node.text.decode("utf-8", errors="ignore"))
    print(context_node)

    actual_prefix, _ = _split_on_point(source_code, target_point)
    
    # Split again in order to have a prefix and a suffix, but do so relatively to the context node.
    # Also ignore the prefix, since we are only interested in truncating the suffix.
    _, actual_truncated_suffix = _split_node(context_node, target_point)
    print("-----------------------")
    print("Prefix")
    print("-----------------------")
    print(repr(actual_prefix))
    print(repr(expected_prefix))

    print("-----------------------")
    print("Suffix")
    print("-----------------------")
    print(repr(actual_truncated_suffix))
    print(repr(expected_suffix))

    assert actual_prefix == expected_prefix
    assert actual_truncated_suffix == expected_suffix


# TODO: move these functions
def _split_on_point(source_code: str, target_point: tuple[int, int]):
    pos = _point_to_position(source_code, target_point)
    prefix = source_code[:pos]
    suffix = source_code[pos:]
    return (prefix, suffix)


def _split_node(node: Node, point: tuple[int, int]):
    point_in_node = _convert_target_point_to_point_in_node(node, point)
    return _split_on_point(node.text.decode("utf-8", errors="ignore"), point_in_node)


def _convert_target_point_to_point_in_node(node: Node, target_point: tuple[int, int]):
    # translate target_point to point_in_node
    row_in_node = target_point[0] - node.start_point[0]
    col_in_node = target_point[1] - node.start_point[1]
    point_in_node = (row_in_node, col_in_node)
    return point_in_node


def _point_to_position(source_code: str, target_point: tuple[int, int]):
    row, col = target_point
    lines = source_code.splitlines()

    if row >= len(lines) or col > len(lines[row]):
        raise ValueError("Invalid target_point")

    pos = 0
    for i in range(row):
        pos += len(lines[i]) + 1
    pos += col
    return pos


def _position_to_point(source_code: str, pos: int):
    lines = source_code.splitlines()
    row = 0
    col = 0
    for line in lines:
        for col in line:
            pos -= 1
            if pos == 0:
                return (row, col)
            col += 1
        line += 1
    raise ValueError("Invalid position")


def _highlight_position(pos, mystring):
    # fix this quadratic loop
    text_highlight = ""
    for i, x in enumerate(mystring):
        if i == pos:
            text_highlight += f"\033[44;33m{x}\033[m"
        else:
            text_highlight += x
    return text_highlight
