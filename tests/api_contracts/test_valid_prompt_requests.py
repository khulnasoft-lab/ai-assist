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
                        "payload": {},
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
                            "params": {},
                        },
                    },
                    {
                        "type": "editor_content",
                        "metadata": {
                            "source": "gitlab-vscode-extension",
                            "version": "1.2.3",
                        },
                        "payload": {
                            "filename": "application.rb",
                            "before_cursor": "require 'active_record/railtie'",
                            "after_cursor": "\nrequire 'action_controller/railtie'",
                            "open_files": [
                                {
                                    "filename": "app/controllers/application_controller.rb",
                                    "content": "class ApplicationController < ActionController::Base...",
                                }
                            ],
                        },
                    },
                ]
            }
        ),
    ],
)
def test_valid_prompt_payloads(request_json):
    jsonschema.validate(request_json, load_schema("prompt"))


@pytest.mark.parametrize(
    ("request_json", "expected_error"),
    [
        ({}, r"'prompt_components' is a required property"),
        ({"prompt_components": []}, r"\[\] is too short"),
        ({"prompt_components": [{}]}, r"'type' is a required property"),
        (
            {"prompt_components": [{"type": "prompt"}]},
            r"'metadata' is a required property",
        ),
        (
            {
                "prompt_components": [
                    {"type": "unsupported", "metadata": {}, "payload": {}}
                ]
            },
            r"'unsupported' is not one of.+",
        ),
        (
            {"prompt_components": [{"type": "prompt", "metadata": {}, "payload": {}}]},
            r"'source' is a required property",
        ),
        (
            {
                "prompt_components": [
                    {
                        "type": "prompt",
                        "metadata": {"source": "gitlab-saas"},
                        "payload": {},
                    }
                ]
            },
            r"'version' is a required property",
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
                    }
                ]
            },
            r"'payload' is a required property",
        ),
    ],
)
def test_invalid_prompt_payloads(request_json, expected_error):
    with pytest.raises(jsonschema.ValidationError, match=expected_error):
        jsonschema.validate(request_json, load_schema("prompt"))
