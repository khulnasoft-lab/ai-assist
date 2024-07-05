import requests
import os
import structlog
import requests

log = structlog.stdlib.get_logger("self_hosted")

def _get_gitlab_version(config):
    try:
        url = f"{config.gitlab_api_url}/version"
        headers = {"PRIVATE-TOKEN": os.environ['GITLAB_API_KEY']}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        version_data = response.json()
        return version_data.get('version', '')
    except requests.RequestException as e:
        log.error("Failed to get GitLab version", error=str(e))
        return None

def download_documentation_index(config, version=None):
    # version = version or _get_gitlab_version(config)
    version = version or "v17.0.0-ee"

    base_path = config.custom_models.documentation_index_dir
    db_path = f"{base_path}/{version}.db"

    if os.path.exists(db_path):
        print(f"Documentation index for version {version} already exists.")
        return

    print(f"Downloading")
    download_url = f"{config.custom_models.documentation_index_source}/{version}/docs.db"
    response = requests.get(download_url)

    if response.status_code != 200:
        log.error("Failed to download documentation index", status_code=response.status_code)
        return

    print(f"Downloaded")

    base_path = config.custom_models.documentation_index_dir
    os.makedirs(os.path.dirname(base_path), exist_ok=True)

    with open(db_path, 'wb') as file:
        file.write(response.content)

    print(f"Done")


