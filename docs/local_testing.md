# Local Testing Guide for AI Gateway

This document provides detailed instructions for testing the AI Gateway in various scenarios. Whether you're running the service standalone or integrated with the monolith, this guide will help you set up your environment for local testing.

## Table of Contents

- [Testing Without the Monolith](#testing-without-the-monolith)
- [Testing With the Monolith](#testing-with-the-monolith)
- [Testing Code Suggestions Locally](#testing-code-suggestions-locally)

## Testing Without the Monolith

To run the AI Gateway without the full GitLab environment:

1. Ensure you have Docker and `docker-compose` installed.
2. Clone the AI Gateway repository and navigate to the project directory.
3. Start the service using Docker Compose: `docker-compose up`
4. The service should now be accessible at `http://localhost:5000`. Use tools like Postman or cURL to send requests to the API endpoints.

## Testing With the Monolith

To integrate and test the AI Gateway with the GitLab monolith:

1. Ensure you have a local instance of GitLab (GDK) running.
2. Update the AI Gateway configuration to point to your local GitLab instance by setting the `AIGW_GITLAB_URL` and `AIGW_GITLAB_API_URL` in your `.env` file: 

```shell
AIGW_GITLAB_URL=http://127.0.0.1:3000/
AIGW_GITLAB_API_URL=http://127.0.0.1:3000/api/v4/
```

3. Follow the steps in [Testing Without the Monolith](#testing-without-the-monolith) to start the AI Gateway.
4. Ensure the necessary feature flags are enabled in your GDK instance to allow communication between the AI Gateway and GitLab.

## Testing Code Suggestions Locally

To test code suggestions functionality:

1. Configure your local AI Gateway and GitLab instance as described in the previous sections.
2. In the GitLab VS Code Extension or any supported client, set the endpoint URL to your local AI Gateway instance, typically `http://localhost:5000`.
3. Use the client to generate code suggestions requests. The AI Gateway should process these requests and return suggestions.

### Additional Tips

- **Debugging**: Use logging and breakpoints within the AI Gateway to troubleshoot issues.
- **Mocking External Services**: For components interacting with external services (e.g., GCP Vertex AI), consider mocking these services to test the integration points.

This guide aims to facilitate a smooth local testing experience for contributors to the AI Gateway project. By following these instructions, developers can ensure their changes work as expected before submitting merge requests.