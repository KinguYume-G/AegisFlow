from __future__ import annotations

import os
from typing import TypedDict
from uuid import uuid4

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from aegisflow_core.runtime.checkpoint import (
    CheckpointIdentity,
    PostgresCheckpointManager,
    build_checkpoint_config,
    validate_checkpoint_config,
)
from aegisflow_core.runtime.checkpoint.postgres import (
    InvalidCheckpointIdentityError,
    strict_checkpoint_serializer,
)


class CounterState(TypedDict):
    value: int


class ApprovalState(TypedDict, total=False):
    prompt: str
    decision: str


def identity() -> CheckpointIdentity:
    return CheckpointIdentity(uuid4(), uuid4(), 2)


def counter_graph(checkpointer):
    builder = StateGraph(CounterState)
    builder.add_node("increment", lambda state: {"value": state["value"] + 1})
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)
    return builder.compile(checkpointer=checkpointer)


def approval_graph(checkpointer):
    def await_approval(state: ApprovalState) -> ApprovalState:
        return {"decision": interrupt({"prompt": state["prompt"]})}

    builder = StateGraph(ApprovalState)
    builder.add_node("await_approval", await_approval)
    builder.add_edge(START, "await_approval")
    builder.add_edge("await_approval", END)
    return builder.compile(checkpointer=checkpointer)


def test_checkpoint_config_binds_tenant_run_and_version() -> None:
    value = identity()
    config = build_checkpoint_config(value)
    assert config["configurable"]["thread_id"] == value.thread_id
    assert config["configurable"]["checkpoint_ns"] == ""
    validate_checkpoint_config(config, value)
    with pytest.raises(InvalidCheckpointIdentityError):
        validate_checkpoint_config(config, CheckpointIdentity(uuid4(), value.run_id, 2))
    with pytest.raises(ValueError):
        CheckpointIdentity(value.tenant_id, value.run_id, 0)


def test_serializer_disables_pickle_and_unrestricted_modules() -> None:
    serializer = strict_checkpoint_serializer()
    assert serializer.pickle_fallback is False
    assert serializer._allowed_msgpack_modules != True  # noqa: E712


@pytest.mark.database
@pytest.mark.asyncio
async def test_postgres_checkpoint_setup_reconstruction_and_tenant_isolation() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required")
    manager = PostgresCheckpointManager(database_url)
    await manager.setup()
    await manager.setup()
    value = identity()
    config = build_checkpoint_config(value)

    async with manager.open() as first_saver:
        first_graph = counter_graph(first_saver)
        assert (await first_graph.ainvoke({"value": 1}, config=config))["value"] == 2
        interrupted = approval_graph(first_saver)
        pending = await interrupted.ainvoke({"prompt": "approve?"}, config=config)
        assert pending["__interrupt__"]

    async with manager.open() as reconstructed_saver:
        reconstructed = approval_graph(reconstructed_saver)
        resumed = await reconstructed.ainvoke(Command(resume="approved"), config=config)
        assert resumed["decision"] == "approved"
        assert await reconstructed_saver.aget_tuple(config) is not None
        other_tenant = CheckpointIdentity(uuid4(), value.run_id, value.workflow_version)
        assert await reconstructed_saver.aget_tuple(
            build_checkpoint_config(other_tenant)
        ) is None
