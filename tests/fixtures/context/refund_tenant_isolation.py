"""Sanitized repository evidence for tenant-isolated refund audit reads."""

# FastAPI and SQLAlchemy queries must include tenant_id when reading refund audits.
# Only the Finance Admin role may request an export; other roles receive HTTP 403.
REFUND_AUDIT_SCOPE = "tenant_id"
