import io
import json

import jsonschema
import pytest

SCHEMA_PATH = "./ai_gateway/api/schemas/"


def load_schema(schema_name: str):
    return json.load(io.open(SCHEMA_PATH + schema_name + ".json"))


@pytest.mark.parametrize(
    ("request_json"),
    [{"prompt_components": [{"type": "prompt", "metadata": {}, "payload": {}}]}],
)
def test_valid_prompt_payloads(request_json):
    jsonschema.validate(request_json, load_schema("prompt"))


@pytest.mark.parametrize(
    ("request_json", "expected_error"),
    [
        ({"prompt_components": []}, r"\[\] is too short"),
        ({"prompt_components": [{}]}, r"'type' is a required property"),
        (
            {"prompt_components": [{"type": "prompt"}]},
            r"'metadata' is a required property",
        ),
        (
            {"prompt_components": [{"type": "prompt", "metadata": {}}]},
            r"'payload' is a required property",
        ),
    ],
)
def test_invalid_prompt_payloads(request_json, expected_error):
    with pytest.raises(jsonschema.ValidationError, match=expected_error):
        jsonschema.validate(request_json, load_schema("prompt"))
