from unittest.mock import patch, mock_open

import pytest

from ai_gateway.experimentation.ast_poc.tag_builder import Tag, TagsBuilder

@pytest.fixture
def tags_builder():
    return TagsBuilder()


@pytest.mark.asyncio
async def test_get_tags_for_file(tags_builder):
    # Create a sample file for testing
    filepath = "test_file.py"
    relative_filepath = "path/to/test_file.py"
    file_content = "def hello_world():\n    print('Hello, World!')"

    with patch("builtins.open", mock_open(read_data=file_content)):
      tags = await tags_builder.get_tags_for_file(filepath, relative_filepath)
    for tag in tags:
      print(tag)
    assert len(tags) == 2
    test_tags = [
      Tag(
        rel_filepath=relative_filepath,
        filepath=filepath,
        name="hello_world",
        kind="def",
        line=0,
        end_line=0,
      ),
      Tag(
        rel_filepath=relative_filepath,
        filepath=filepath,
        name="print",
        kind="ref",
        line=1,
        end_line=1,
      )
    ]
    for tag in test_tags:
      assert tag in tags



@pytest.mark.asyncio
async def test_get_tags_for_file_empty(tags_builder):
    filepath = "test_file.py"
    relative_filepath = "path/to/test_file.py"
    file_content = ""

    with patch("builtins.open", mock_open(read_data=file_content)):
        tags = await tags_builder.get_tags_for_file(filepath, relative_filepath)

    assert tags == []


@pytest.mark.asyncio
async def test_get_tags_for_file_exception(tags_builder):
    filepath = "test_file.py"
    relative_filepath = "path/to/test_file.py"

    with patch("builtins.open", side_effect=Exception("File not found")):
        tags = await tags_builder.get_tags_for_file(filepath, relative_filepath)

    assert tags == []


def test_read_file(tags_builder):
    filepath = "test_file.py"
    file_content = "def hello_world():\n    print('Hello, World!')"

    with patch("builtins.open", mock_open(read_data=file_content)):
        content = tags_builder._read_file(filepath)

    assert content == file_content


@pytest.mark.asyncio
async def test_get_scm_file_cached(tags_builder):
    lang = "python"
    scm_content = "scm content"
    tags_builder.scm_cache[lang] = scm_content

    result = await tags_builder._get_scm_file(lang)

    assert result == scm_content


@pytest.mark.asyncio
async def test_get_scm_file_not_found(tags_builder):
    lang = "unknown"

    with patch("pkg_resources.resource_filename", side_effect=KeyError):
        result = await tags_builder._get_scm_file(lang)

    assert result is None


@pytest.mark.asyncio
async def test_get_scm_file_read(tags_builder):
    lang = "python"
    scm_content = "scm content"
    scm_filepath = "path/to/queries/tree-sitter-python-tags.scm"

    with patch("pkg_resources.resource_filename", return_value=scm_filepath):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=scm_content):
                result = await tags_builder._get_scm_file(lang)

    assert result == scm_content
    assert tags_builder.scm_cache[lang] == scm_content