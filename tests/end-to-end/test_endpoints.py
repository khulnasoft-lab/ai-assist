import os

import pytest
import requests

prompt = {
    "prompt_version": 1,
    "project_path": "gitlab/gitlab-org",
    "project_id": 278964,
    "current_file": {
        "file_name": "main.py",
        "content_above_cursor": "# Test the code suggestions API\n",
        "content_below_cursor": "",
    },
}


def oidc_token(gitlab, token_var):
    headers = {
        "Authorization": f"Bearer {os.getenv(token_var)}",
        "Content-Type": "application/json",
    }
    r = requests.post(
        f"https://{gitlab}/api/v4/code_suggestions/tokens", headers=headers
    )
    data = r.json()
    return data["access_token"]


@pytest.mark.parametrize(
    "gateway,gitlab,token_var",
    [
        (
            "model-gateway-n2bsxg.staging.runway.gitlab.net",
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
def test_completions_endpoint(gateway, gitlab, token_var):
    headers = {
        "Authorization": f"Bearer {oidc_token(gitlab, token_var)}",
        "X-Gitlab-Authentication-Type": "oidc",
        "Content-Type": "application/json",
    }
    r = requests.post(f"https://{gateway}/v2/completions", json=prompt, headers=headers)
    assert r.status_code == 200

    data = r.json()
    assert len(data["choices"][0]["text"]) > 0, "The suggestion should not be blank"
    assert data["model"]["lang"] == "python"
    assert data["object"] == "text_completion"
