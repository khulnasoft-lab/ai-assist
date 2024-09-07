# Semantic search for public data

You can use `POST /v1/search/(search-app-name)` endpoint in AI Gateway for performing semantic search on public data.

- [Architecture overview](https://docs.gitlab.com/ee/architecture/blueprints/gitlab_rag/vertex_ai_search.html)
- [Implementation details](https://docs.gitlab.com/ee/architecture/blueprints/gitlab_duo_rag/vertex_ai_search.html)

## Data ingestion and refreshing

### GitLab documentations

Input:

| Key                             | Type   | Example                                    |
| ------------------------------- | ------ | ------------------------------------------ |
| `GCP_PROJECT_NAME`              | String | `ai-enablement-dev-69497ba7`               |
| `SEARCH_APP_NAME`               | String | `gitlab-docs`                              |
| `GITLAB_DOCS_REPO`              | String | `https://gitlab.com/gitlab-org/gitlab.git` |
| `GITLAB_DOCS_REPO_REF`          | String | `master`                                   |
| `GITLAB_DOCS_CLONE_DIR`         | String | `/tmp/gitlab-org/gitlab`                   |
| `GITLAB_DOCS_JSONL_EXPORT_PATH` | String | `/tmp/gitlab-org/gitlab/docs.jsonl`        |
| `GITLAB_DOCS_WEB_ROOT_URL`      | String | `https://gitlab.com/help`                  |

Process:

1. Download GitLab doc from `GITLAB_DOCS_REPO` and `GITLAB_DOCS_REPO_REF` to `GITLAB_DOCS_CLONE_DIR`.
1. Parse docs and export as JSONL file to `GITLAB_DOCS_JSONL_EXPORT_PATH`.
1. Read the GitLab version from `VERSION` file. For example, `17.0.0-pre`.
1. Convert the GitLab version to datastore version `<major>-<minor>`. For example, `17.0.0-pre` becomes
   `17-0`.
1. Construct the data store ID `SEARCH_APP_NAME-<datastore_version>`. App name is same with this. For example,
   `gitlab-docs-17-0`.`
1. Construct the BigQuery table ID `GCP_PROJECT_NAME.<data_store_id>.<YYYY-MM-dd-HH-mm-ss>`. For example,
   `ai-enablement-dev-69497ba7.gitlab_docs_17_0.2024-04-25-12-43-30`.
1. Create a new BigQuery table from the JSONL file exported to `GITLAB_DOCS_JSONL_EXPORT_PATH`.
1. Create a new data store in Vertex AI Search that imports the BigQuery table. If the data store already
   exists, import the BigQuery table with incremental or full update. See
   <https://cloud.google.com/generative-ai-app-builder/docs/refresh-data>.
1. Create a new search app in Vertex AI Search that connects to the data store. If the search app already exists, skip this step.

As a result, the search app `gitlab-docs-17-0` is connected to the data store `gitlab-docs-17-0`, which was imported from the bigquery table `ai-enablement-dev-69497ba7.gitlab_docs_17_0.2024-04-25-12-43-30`. 

A few notes:

- Vertex AI Search was renamed to Agent Builder.
- In AI Gateway project, CI/CD scheduled pipeline runs the ingestion to `ai-enablement-dev-69497ba7` GCP project 03:00 AM UTC every day.
  See `ingest:dev` job in the pipelines.

### Run locally

Login to the GCP via Application Default Credentials (ADC):

```shell
gcloud auth application-default login
gcloud auth application-default set-quota-project ai-enablement-dev-69497ba7
```

Run the following script in terminal:

```shell
export GCP_PROJECT_NAME="ai-enablement-dev-69497ba7"
export SEARCH_APP_NAME="gitlab-docs"
export GITLAB_DOCS_REPO="https://gitlab.com/gitlab-org/gitlab.git"
export GITLAB_DOCS_REPO_REF="master"
export GITLAB_DOCS_CLONE_DIR="/tmp/gitlab-org/gitlab"
export GITLAB_DOCS_JSONL_EXPORT_PATH="/tmp/gitlab-org/gitlab/docs.jsonl"
export GITLAB_DOCS_WEB_ROOT_URL="https://gitlab.com/help"

make ingest
```

or use Docker image:

```shell
docker run \
    -e 'GCP_PROJECT_NAME=ai-enablement-dev-69497ba7' \
    -e 'SEARCH_APP_NAME=gitlab-docs' \
    -e 'GITLAB_DOCS_REPO=https://gitlab.com/gitlab-org/gitlab.git' \
    -e 'GITLAB_DOCS_REPO_REF=master' \
    -e 'GITLAB_DOCS_CLONE_DIR=/tmp/gitlab-org/gitlab' \
    -e 'GITLAB_DOCS_JSONL_EXPORT_PATH=/tmp/gitlab-org/gitlab/docs.jsonl' \
    -e 'GITLAB_DOCS_WEB_ROOT_URL=https://gitlab.com/help' \
    -e 'GOOGLE_APPLICATION_CREDENTIALS=/gcloud-config/application_default_credentials.json' \
    -v "$HOME/.config/gcloud/application_default_credentials.json:/gcloud-config/application_default_credentials.json" \
    registry.gitlab.com/gitlab-org/modelops/applied-ml/code-suggestions/ai-assist/ingest:<SHA>
```

### Test search app in GCP console

You can test a search app in [GCP console](https://console.cloud.google.com/home).

1. Visit **"Your GCP project" > Agent Builder > Apps > "Your app name" > Preview** in GCP.
1. Test a query if it returns relevant chunks.

Here is a [preview app for GitLab documentations](https://console.cloud.google.com/gen-app-builder/locations/global/engines/gitlab-docs-17-0/preview/search?project=ai-enablement-dev-69497ba7).

### Further iteration

- [Generalize ingestion process for any public data](https://gitlab.com/gitlab-org/modelops/applied-ml/code-suggestions/ai-assist/-/issues/446).
- [Replace Ruby parser by Python parser](https://gitlab.com/gitlab-org/modelops/applied-ml/code-suggestions/ai-assist/-/issues/447).

## Search API in AI Gateway

1. `POST /v1/search/(search-app-name)` is requested.
1. If the search app depends on GitLab version:
   1. Get the GitLab version from `metadata.version` parameter.
   1. Convert the GitLab version to datastore version `<major>-<minor>`. For example, `17.0.0-pre` becomes
      `17-0`.
   1. Construct the data store ID `<name>-<version>`. App name is same with this. For example,
      `gitlab-docs-17-0`.
1. Request to the Vertex AI Search with the data store ID.
   1. If the request encountered an error, it falls back to a stable data store which is hard-coded in AI
      Gateway. This process would be improved in the future to be more resilient. Example scenarios:
      1. The data store ID doesn't exist yet (for example, GitLab-Rails bump the `VERSION` and its deployed to
         GitLab.com, but the ingestion pipeline has not run yet).
      1. The data is still being processed/indexed by Vertex AI Search, which usually takes 5-10 minutes.

## Check usage quota in GCP console

You can check usage quota in [GCP console](https://console.cloud.google.com/home).

1. Visit **"Your Google Cloud project" > API & Services > Discovery Engine API > QUOTAS & SYSTEM LIMITS** in Google Cloud.
1. Check **Current usage percentage**. If the value is saturated, [search API in AI Gateway](#search-api-in-ai-gateway) or [ingestion process](#data-ingestion-and-refreshing) could fail.

Here is a [quota and usage percentage for `ai-enablement-dev-69497ba7` project](https://console.cloud.google.com/apis/api/discoveryengine.googleapis.com/quotas?project=ai-enablement-dev-69497ba7).

## Manually create Google Cloud app

The Google Cloud search apps are automatically created for each milestone, but you can manually set up your own for testing purposes:

1. Visit https://console.cloud.google.com/gen-app-builder/data-stores/create?project=ai-enablement-dev-69497ba7
  1. For "Native sources", choose "BigQuery".
  1. For "BigQuery path", choose "chunked_markdown" (sm_gitlab_docs_structured_test)
  1. Keep default "Structured - BigQuery table with your own schema"
  1. Keep default "Location" as "global"
  1. Set a data store name (e.g. "foo-gitlab-docs-structured")
  1. Click "Create"
1. Visit https://console.cloud.google.com/gen-app-builder/engines/create?project=ai-enablement-dev-69497ba7
  1. For "Select app type", choose "Search"
  1. Keep default "Generic"
  1. Set an app name (e.g. "foo-gitlab-docs-structured")
  1. For "Company name", set "GitLab"
  1. Keep default "Location" as "global"
  1. Click "Continue"
  1. Choose the data store you created earlier
  1. Click "Create"
1. You can see that it is processing data. This will take around 5 minutes to complete.
1. Temporarily update `_get_data_store_id` method to return the app name you created in order to test it.

