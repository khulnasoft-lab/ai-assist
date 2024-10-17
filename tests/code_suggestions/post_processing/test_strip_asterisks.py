import pytest

from ai_gateway.code_suggestions.processing.post.ops import strip_asterisks

COMPLETION_RUBY_1_1 = """
****************************
    expect(person.fullname).to eq('First')
  end
""".strip(
    "\n"
)

COMPLETION_RUBY_1_2 = """
    ****************************
    expect(person.fullname).to eq('First')
""".strip(
    "\n"
)

COMPLETION_RUBY_1_3 = "\n\t\t    ****************************\nend"
COMPLETION_RUBY_1_4 = "expect(person.fullname).to eq('First')"


@pytest.mark.parametrize(
    ("completion", "expected_result"),
    [
        (COMPLETION_RUBY_1_1, "expect(person.fullname).to eq('First')\n  end"),
        (COMPLETION_RUBY_1_2, "    expect(person.fullname).to eq('First')"),
        (COMPLETION_RUBY_1_3, "\n\t\t    end"),
        (COMPLETION_RUBY_1_4, "expect(person.fullname).to eq('First')"),
    ],
)
def test_strip_asterisks(completion: str, expected_result: str):
    actual_result = strip_asterisks(completion)

    assert actual_result == expected_result
