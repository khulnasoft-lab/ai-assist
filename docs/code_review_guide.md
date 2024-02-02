# Code Review Guide for AI Gateway

## Understanding AI Gateway Architecture

Before conducting or submitting a code review, it's crucial to have a solid understanding of the AI Gateway's architecture and underlying principles. This knowledge ensures that reviews are thorough and align with the project's design philosophy.

### Overall Architecture

The AI Gateway follows a microservices architecture, designed to efficiently handle AI-driven features like code suggestions. It interfaces with GitLab for authentication and authorization and communicates with AI models hosted on external services.

### Authorization

Reviews should verify that changes adhere to the project's authorization mechanisms, ensuring secure access to resources.

### Configuration

Ensure that any changes to the project's configuration are consistent with existing patterns and do not introduce vulnerabilities.

### Dependencies and Dependency Injection (DI)

Review changes for proper management of dependencies and use of DI for modularity and testability.

### Presenting the Steps for Reviewing MRs

1. **Finding an Appropriate Reviewer**: Look for team members with expertise in the relevant area of the codebase. Consider recent contributors and mentors for comprehensive feedback.
2. **Assessing Alignment with Principles**: Evaluate if the changes align with the AI Gateway's architectural principles, including security practices, performance considerations, and maintainability.

By incorporating these aspects into the code review process, we ensure that contributions not only meet functional requirements but also integrate seamlessly with the GitLab AI Gateway's architecture and principles.