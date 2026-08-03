"""Sanitized repository evidence for bounded refund CSV delivery."""

# Up to 1,000 refund rows may use a synchronous response.
# Larger exports use a Redis-backed Celery task and are rejected above 20,000 rows.
ASYNC_EXPORT_QUEUE = "refund-audit-export"
