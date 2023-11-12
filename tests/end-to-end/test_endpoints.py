import os

import pytest
import requests

# This test sends the prompt below to the AI-gateway at the addresses specified (parameterized as `gateway`) and checks
# for a response (of non-zero length).
# It requires the environment variable `GITLAB_PAT_STAGING` to be a personal access token on staging with API scope.
# The test can be run via docker compose by running `make test-e2e-local`, in which case GITLAB_PAT_STAGING should be
# included in your `.env` file.

prompt = {
    "prompt_version": 1,
    "project_path": "gitlab/gitlab-org",
    "project_id": 278964,
    "current_file": {
        "file_name": "main.py",
        "content_above_cursor": "def reverse_string(s):\n    return s[::-1]\ndef test_empty_input_string()",
        "content_below_cursor": "",
    },
}


@pytest.fixture
def oidc_token(gitlab, token_var):
    headers = {
        "Authorization": f"Bearer {os.getenv(token_var)}",
        "Content-Type": "application/json",
    }
    r = requests.post(
        f"https://{gitlab}/api/v4/code_suggestions/tokens", headers=headers, timeout=10
    )
    data = r.json()
    return data["access_token"]


@pytest.mark.parametrize(
    "gateway,gitlab,token_var",
    [
        (
            "ai-gateway.staging.runway.gitlab.net",
            "staging.gitlab.com",
            "GITLAB_PAT_STAGING",
        ),
        (
            "codesuggestions.staging.gitlab.com",
            "staging.gitlab.com",
            "GITLAB_PAT_STAGING",
        ),
    ],
)
def test_completions_endpoint(gateway, oidc_token):
    headers = {
        "Authorization": f"Bearer {oidc_token}",
        "X-Gitlab-Authentication-Type": "oidc",
        "Content-Type": "application/json",
    }
    r = requests.post(
        f"https://{gateway}/v2/completions", json=prompt, headers=headers, timeout=1
    )
    assert r.status_code == 200

    data = r.json()
    assert len(data["choices"][0]["text"]) > 0, "The suggestion should not be blank"
    assert data["model"]["lang"] == "python"
    assert data["object"] == "text_completion"
