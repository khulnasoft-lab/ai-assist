import pytest

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


@pytest.mark.parametrize(
    (
        "lang_id",
        "source_code",
        "target_point",
        "expected_prefix",
        "expected_suffix",
    ),
    [
        ( # Test context at function level
            LanguageId.PYTHON,
            """
def sum(a, b):
    return 

def subtract(a, b):
    return a - b
""",
            (1, 10),
"""
def sum(a, b):
    return
""",
            "",
        ),
        ( # Test context at module level
            LanguageId.PYTHON,
            """
def sum(a, b):
    return 

def subtract(a, b):
    return a - b
""",
            (2, 0),
"""
def sum(a, b):
    return 

""",
"""

def subtract(a, b):
    return a - b

""",
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
    # skip the first \n [and last \n]
    source_code = source_code[1:]
    expected_prefix = expected_prefix[1:-1]
    expected_suffix = expected_suffix[1:-1]
    print(f"{target_point=}")
    print("-----------------------")
    print("source_code:")
    print("-----------------------")
    print(source_code)

    # Extract relevant context around the cursor
    parser = CodeParser.from_language_id(source_code, lang_id)
    context_node = parser.context_near_cursor(target_point)
    assert context_node is not None
    actual_context = context_node.text.decode("utf-8", errors="ignore")
    print("-----------------------")
    print("actual_context:")
    print(context_node)
    print("-----------------------")
    print(actual_context)

    # Split again in order to have a prefix and a suffix again
    actual_prefix, actual_suffix = _split_on_point(actual_context, target_point)
    print("-----------------------")
    print("Prefix")
    print("-----------------------")
    print(repr(actual_prefix))
    print(repr(expected_prefix))

    print("-----------------------")
    print("Suffix")
    print("-----------------------")
    print(repr(actual_suffix))
    print(repr(expected_suffix))

    assert actual_prefix == expected_prefix
    assert actual_suffix == expected_suffix


# TODO: move these functions
def _split_on_point(source_code: str, target_point: tuple[int, int]):
    pos = _point_to_position(source_code, target_point)
    prefix = source_code[:pos]
    suffix = source_code[pos:]
    return (prefix, suffix)


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
