import io
import json

import jsonschema
import pytest

SCHEMA_PATH = "./ai_gateway/api/schemas/"


def load_schema(schema_name: str):
    return json.load(io.open(SCHEMA_PATH + schema_name + ".json"))


@pytest.mark.parametrize(
    ("request_json"),
    [
        (
            {
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-saas",
                            "version": "66b71a300bf2f85a3ec728e056a6699497a9f86a",
                        },
                        "payload": {
                            "content": "this is a prompt string",
                            "provider": "vertex-ai",
                            "model": "code-gecko",
                        },
                    }
                ]
            }
        ),
        (
            {
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-saas",
                            "version": "66b71a300bf2f85a3ec728e056a6699497a9f86a",
                        },
                        "payload": {
                            "content": "this is a prompt string",
                            "provider": "vertex-ai",
                            "model": "code-gecko",
                            "params": {"custom_param": 42},
                        },
                    }
                ]
            }
        ),
    ],
)
def test_valid_prompt_payloads(request_json):
    jsonschema.validate(request_json, load_schema("prompt"))


@pytest.mark.parametrize(
    ("scenario", "request_json", "expected_error"),
    [
        ("prompt_components missing", {}, "'prompt_components' is a required property"),
        ("prompt_components is empty", {"prompt_components": []}, "[] is too short"),
        ("type missing", {"prompt_components": [{}]}, "'type' is a required property"),
        (
            "metadata missing",
            {"prompt_components": [{"type": "prompt"}]},
            "'metadata' is a required property",
        ),
        (
            "unsupported type",
            {
                "prompt_components": [
                    {
                        "type": "unsupported",
                        "metadata": {
                            "source": "gitlab-saas",
                            "version": "66b71a300bf2f85a3ec728e056a6699497a9f86a",
                        },
                        "payload": {
                            "content": "this is a prompt string",
                            "provider": "vertex-ai",
                            "model": "code-gecko",
                        },
                    }
                ]
            },
            "'unsupported' is not one of",
        ),
        (
            "metadata.source missing",
            {
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {},
                        "payload": {
                            "content": "this is a prompt string",
                            "provider": "vertex-ai",
                            "model": "code-gecko",
                        },
                    }
                ]
            },
            "'source' is a required property",
        ),
        (
            "metadata.version missing",
            {
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {"source": "gitlab-saas"},
                        "payload": {
                            "content": "this is a prompt string",
                            "provider": "vertex-ai",
                            "model": "code-gecko",
                        },
                    }
                ]
            },
            "'version' is a required property",
        ),
        (
            "payload missing",
            {
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-saas",
                            "version": "66b71a300bf2f85a3ec728e056a6699497a9f86a",
                        },
                    }
                ]
            },
            "'payload' is a required property",
        ),
        (
            "payload.content missing",
            {
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-saas",
                            "version": "66b71a300bf2f85a3ec728e056a6699497a9f86a",
                        },
                        "payload": {},
                    }
                ]
            },
            "'content' is a required property",
        ),
        (
            "payload.provider missing",
            {
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-saas",
                            "version": "66b71a300bf2f85a3ec728e056a6699497a9f86a",
                        },
                        "payload": {"content": "this is a prompt"},
                    }
                ]
            },
            "'provider' is a required property",
        ),
        (
            "payload.model missing",
            {
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {
                            "source": "gitlab-saas",
                            "version": "66b71a300bf2f85a3ec728e056a6699497a9f86a",
                        },
                        "payload": {
                            "content": "this is a prompt",
                            "provider": "vertex-ai",
                        },
                    }
                ]
            },
            "'model' is a required property",
        ),
    ],
)
def test_invalid_prompt_payloads(scenario, request_json, expected_error):
    with pytest.raises(jsonschema.ValidationError) as ex:
        jsonschema.validate(request_json, load_schema("prompt"))

    assert expected_error in str(ex.value), "scenario failed: " + scenario
