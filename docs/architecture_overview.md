# Architecture Overview of AI Gateway

This document provides a comprehensive overview of the architecture of the AI Gateway, detailing its components, their interactions, and the principles guiding its design. The AI Gateway serves as a bridge between GitLab users and AI-driven features, facilitating code suggestions, and other AI-powered functionalities.

## Table of Contents

- [High-Level Architecture](#high-level-architecture)
- [Component Overview](#component-overview)
  - [Client](#client)
  - [AI Gateway API](#ai-gateway-api)
  - [GitLab API](#gitlab-api)
- [Code Suggestions Workflow](#code-suggestions-workflow)
- [Security and Authentication](#security-and-authentication)
- [Testing and Deployment](#testing-and-deployment)
- [Technologies Used](#technologies-used)

## High-Level Architecture

The AI Gateway architecture is designed following [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) principles, which aim to create systems that are independent of frameworks, UI, and databases. This approach allows for more flexible and maintainable code.

The system is divided into several layers:
- **Entities**: The business objects of the application.
- **Use Cases**: The business rules and features the application implements.
- **Interface Adapters**: Convert data between the most convenient format for use cases and entities, and the format needed for external agencies like databases and web.
- **Frameworks and Drivers**: The outermost layer consisting of frameworks, tools, and drivers.

## Component Overview

### Client

Clients are the consumers of the AI Gateway, such as the GitLab VS Code Extension or the GitLab Web IDE. They are responsible for sending code snippets to the AI Gateway and presenting the suggestions returned by the AI models to the users.

### AI Gateway API

The AI Gateway API is the core component that interfaces with both the clients and the AI models. It is responsible for:
- Authenticating requests using GitLab JSON Web Key Sets (JWKS).
- Processing and formatting requests for the AI models.
- Communicating with AI models hosted on GCP Vertex AI.
- Parsing and returning the AI models' responses to the clients.

### GitLab API

The GitLab API is used for authentication and authorization. It provides the JWKS used by the AI Gateway to validate incoming requests.

## Code Suggestions Workflow

1. The client sends a request for code suggestions to the AI Gateway, including the code snippet and context.
2. The AI Gateway authenticates the request using JWKS from GitLab.
3. The request is processed and sent to the appropriate AI model.
4. The AI model returns suggestions, which are parsed and formatted by the AI Gateway.
5. The AI Gateway returns the suggestions to the client.

## Security and Authentication

Security is a critical aspect of the AI Gateway. It uses OAuth and JWT tokens for secure communication between clients and the AI Gateway, and between the AI Gateway and GitLab. The use of GitLab JWKS for request validation adds an additional layer of security.

## Testing and Deployment

The AI Gateway employs a comprehensive suite of automated tests, including unit tests, integration tests, and end-to-end tests. Continuous Integration (CI) and Continuous Deployment (CD) pipelines facilitate the testing, building, and deployment processes, ensuring that new changes are automatically tested and deployed to production environments.

## Technologies Used

- **FastAPI**: For building the API, thanks to its performance and ease of use for creating RESTful APIs.
- **Pydantic**: For data validation and settings management.
- **HTTPX**: For asynchronous HTTP requests.
- **GCP Vertex AI**: For hosting and managing AI models.

This architecture overview provides a high-level understanding of the AI Gateway's design and operation. It is intended to guide contributors and maintainers in understanding how the system works as a whole and how individual components fit into the larger picture.