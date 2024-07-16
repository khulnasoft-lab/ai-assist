from enum import Enum


# Make sure these unit primitives are defined in `ee/config/cloud_connector/access_data.yml`
class GitLabUnitPrimitive(str, Enum):
    ANALYZE_CI_JOB_FAILURE = "analyze_ci_job_failure"
    CATEGORIZE_DUO_CHAT_QUESTION = "categorize_duo_chat_question"
    CODE_SUGGESTIONS = "code_suggestions"
    DOCUMENTATION_SEARCH = "documentation_search"
    DUO_CHAT = "duo_chat"
    EXPLAIN_CODE = "explain_code"
    EXPLAIN_VULNERABILITY = "explain_vulnerability"
    FILL_IN_MERGE_REQUEST_TEMPLATE = "fill_in_merge_request_template"
    GENERATE_COMMIT_MESSAGE = "generate_commit_message"
    GENERATE_CUBE_QUERY = "generate_cube_query"
    GENERATE_ISSUE_DESCRIPTION = "generate_issue_description"
    GLAB_ASK_GIT_COMMAND = "glab_ask_git_command"
    RESOLVE_VULNERABILITY = "resolve_vulnerability"
    REVIEW_MERGE_REQUEST = "review_merge_request"
    SEMANTIC_SEARCH_ISSUE = "semantic_search_issue"
    SUMMARIZE_ISSUE_DISCUSSIONS = "summarize_issue_discussions"
    SUMMARIZE_MERGE_REQUEST = "summarize_merge_request"
    SUMMARIZE_REVIEW = "summarize_review"
    SUMMARIZE_SUBMITTED_REVIEW = "summarize_submitted_review"
    SUMMARIZE_COMMENTS = "summarize_comments"
