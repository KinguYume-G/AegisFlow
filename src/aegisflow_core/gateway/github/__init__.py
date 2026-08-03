"""GitHub App authentication and webhook gateway."""

from aegisflow_core.gateway.github.auth import (
    GitHubAppAuthError,
    InstallationToken,
    InstallationTokenProvider,
)
from aegisflow_core.gateway.github.webhook import (
    InMemoryReplayGuard,
    ReplayClaim,
    WebhookRejectionReason,
    WebhookVerificationResult,
    router,
    verify_webhook,
)
from aegisflow_core.gateway.github.read_tools import (
    FileContent,
    GitHubReadClient,
    IssueSnapshot,
    PullRequestDiff,
    PullRequestSnapshot,
    RepositoryTree,
    TreeEntry,
)

__all__ = [
    "GitHubAppAuthError",
    "InMemoryReplayGuard",
    "InstallationToken",
    "InstallationTokenProvider",
    "FileContent",
    "GitHubReadClient",
    "IssueSnapshot",
    "PullRequestDiff",
    "PullRequestSnapshot",
    "RepositoryTree",
    "ReplayClaim",
    "WebhookRejectionReason",
    "WebhookVerificationResult",
    "TreeEntry",
    "router",
    "verify_webhook",
]
