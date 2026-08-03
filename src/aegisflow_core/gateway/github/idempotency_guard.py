"""Adapter from GitHub tool commands to the persistent idempotency ledger."""

from hashlib import sha256
import json
from uuid import UUID

from aegisflow_core.control_plane.idempotency_ledger import IdempotencyLedger
from aegisflow_core.packs.delivery.contracts.idempotency import ClaimResult, IdempotentCommand
from aegisflow_core.packs.delivery.contracts.idempotency import Execute, InProgress, Reuse
from aegisflow_core.gateway.github.webhook import WebhookDispatcher, WebhookVerificationResult


class PostgresIdempotencyGuard:
    def __init__(self, ledger: IdempotencyLedger) -> None:
        self._ledger = ledger
        self._claims: dict[UUID, str] = {}

    async def begin(self, command: IdempotentCommand) -> ClaimResult:
        result = await self._ledger.begin(
            scope=command.scope,
            idempotency_key=command.idempotency_key,
            tenant_id=command.tenant_id,
            arguments_hash=command.arguments_hash,
            run_id=command.run_id,
            step_id=command.step_id,
            tool_name=command.tool_name,
        )
        claim_token = getattr(result, "claim_token", None)
        if isinstance(claim_token, UUID):
            self._claims[claim_token] = command.idempotency_key
        return result

    async def complete(self, claim_token: UUID, result_reference: str) -> None:
        key = self._claims.pop(claim_token, None)
        if key is None:
            raise KeyError("unknown idempotency claim token")
        await self._ledger.complete(
            key, claim_token=claim_token, result_reference=result_reference
        )

    async def fail(self, claim_token: UUID, retryable: bool, reason: str) -> None:
        key = self._claims.pop(claim_token, None)
        if key is None:
            raise KeyError("unknown idempotency claim token")
        await self._ledger.fail(
            key, claim_token=claim_token, retryable=retryable, reason=reason
        )


class LedgerWebhookDispatcher:
    """Persistently claim a verified delivery before invoking Gate 1B."""

    def __init__(
        self,
        *,
        ledger: IdempotencyLedger,
        tenant_id: UUID,
        inner: WebhookDispatcher,
    ) -> None:
        self._ledger = ledger
        self._tenant_id = tenant_id
        self._inner = inner

    async def dispatch(self, event: WebhookVerificationResult) -> None:
        payload_hash = sha256(
            json.dumps(event.payload or {}, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        key = sha256(
            f"{event.installation_id}\0{event.delivery_id}".encode()
        ).hexdigest()
        claim = await self._ledger.begin(
            scope="webhook_delivery",
            idempotency_key=key,
            tenant_id=self._tenant_id,
            arguments_hash=payload_hash,
            run_id=None,
            step_id=None,
            tool_name=None,
        )
        if isinstance(claim, (Reuse, InProgress)):
            return
        if not isinstance(claim, Execute):
            raise RuntimeError("webhook delivery previously failed permanently")
        try:
            await self._inner.dispatch(event)
        except Exception as exc:
            await self._ledger.fail(
                key,
                claim_token=claim.claim_token,
                retryable=True,
                reason=type(exc).__name__,
            )
            raise
        await self._ledger.complete(
            key,
            claim_token=claim.claim_token,
            result_reference=f"dispatched:{event.delivery_id}",
        )
