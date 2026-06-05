"""User-facing Bedrock error messages."""

from __future__ import annotations

from botocore.exceptions import ClientError  # pyright: ignore[reportMissingTypeStubs]


def bedrock_user_error_message(exc: BaseException) -> str:
    """Map Bedrock client errors to actionable user-facing messages."""
    if isinstance(exc, ClientError):
        error_message = exc.response.get("Error", {}).get("Message", str(exc))
        lowered = error_message.lower()
        if "use case" in lowered:
            return (
                "This AI model is not enabled for your AWS account yet. "
                "Complete the Anthropic use-case form in the Bedrock console, "
                "or contact your administrator."
            )
        if "marketplace" in lowered or "aws-marketplace" in lowered:
            return (
                "This AI model requires AWS Marketplace access on the production API role. "
                "Ask your administrator to redeploy with marketplace permissions, or retry "
                "after a few minutes if access was just enabled."
            )
        return f"Bedrock request failed: {error_message}"
    return "Bedrock request failed"
