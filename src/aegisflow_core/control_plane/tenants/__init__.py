"""Explicit tenant-scoped persistence boundary."""

from aegisflow_core.control_plane.tenants.scope import (
    TenantScope,
    TenantScopeRequired,
    TenantScopeViolation,
    TenantSession,
)

__all__ = [
    "TenantScope",
    "TenantScopeRequired",
    "TenantScopeViolation",
    "TenantSession",
]
