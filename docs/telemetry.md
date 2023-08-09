# Telemetry

Clients of the [Completions](https://gitlab.com/gitlab-org/modelops/applied-ml/code-suggestions/ai-assist/-/blob/main/README.md#completions) endpoint should send telemetry data along with each request. The data should be separated for each unique combination of model, engine, and language.

## Requests

The `requests` field of each object inside the `telemetry` array should be the number of previously requested completions.

## Accepts

The `accepts` field of each object inside the `telemetry` array should be the number of previously accepted completions.

## Errors

The `errors` field of each object inside the `telemetry` array should be the number of previously failed completions.
