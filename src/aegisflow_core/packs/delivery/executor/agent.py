"""Bounded, deterministic Executor orchestration."""

from collections.abc import Mapping
import difflib
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

from aegisflow_core.gateway.sandbox.runner import SandboxRequest, SandboxRunner, TestProfile
from aegisflow_core.packs.delivery.contracts.execution_result import ExecutionResult, TestOutcome
from aegisflow_core.packs.delivery.contracts.plan import Plan
from aegisflow_core.packs.delivery.executor.ports import PatchReasoner

MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES = 1000, 1_000_000, 10_000_000


class ExecutorNodeError(RuntimeError):
    def __init__(self, stage: Literal["apply", "sandbox", "diff"], cause_type: str) -> None:
        self.stage, self.cause_type = stage, cause_type
        super().__init__(f"executor {stage} failed: {cause_type}")


def _safe_path(root: Path, relative: str) -> Path:
    posix, windows = PurePosixPath(relative), PureWindowsPath(relative)
    if not relative or posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts:
        raise ValueError("modification path must be repository-relative")
    target = root.joinpath(*posix.parts)
    root_resolved = root.resolve()
    if target.exists() and target.is_symlink():
        raise ValueError("symlink modifications are forbidden")
    if root_resolved not in target.resolve(strict=False).parents:
        raise ValueError("modification escapes workspace")
    return target


def _read(root: Path) -> dict[str, str]:
    files = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    if len(files) > MAX_FILES:
        raise ValueError("workspace file count exceeds limit")
    result, total = {}, 0
    for path in files:
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("workspace file exceeds limit")
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("workspace exceeds total limit")
        result[path.relative_to(root).as_posix()] = data.decode("utf-8")
    return result


def _diff(before: Mapping[str, str], after: Mapping[str, str]) -> tuple[str, list[str]]:
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    patch = "".join(line for path in changed for line in difflib.unified_diff(
        before.get(path, "").splitlines(keepends=True), after.get(path, "").splitlines(keepends=True),
        fromfile=f"a/{path}", tofile=f"b/{path}",
    ))
    if len(patch.encode()) > 1_000_000:
        raise ValueError("patch exceeds limit")
    return patch, changed


class ExecutorAgent:
    def __init__(self, reasoner: PatchReasoner) -> None:
        self._reasoner = reasoner

    def execute(self, plan: Plan, workspace_source: Path, sandbox_runner: SandboxRunner,
                test_profile: TestProfile) -> ExecutionResult:
        try:
            original = _read(workspace_source)
            modifications = self._reasoner.generate_patch(plan, original)
            for relative, content in modifications.items():
                data = content.encode()
                if len(data) > MAX_FILE_BYTES:
                    raise ValueError("modified file exceeds limit")
                target = _safe_path(workspace_source, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        except Exception as exc:
            raise ExecutorNodeError("apply", type(exc).__name__) from None
        try:
            sandbox = sandbox_runner.run(SandboxRequest(workspace_source=workspace_source, test_profile=test_profile))
        except Exception as exc:
            raise ExecutorNodeError("sandbox", type(exc).__name__) from None
        try:
            patch, changed = _diff(original, _read(sandbox.workspace_output))
        except Exception as exc:
            raise ExecutorNodeError("diff", type(exc).__name__) from None
        if sandbox.status == "completed":
            status = "passed" if sandbox.exit_code == 0 else "failed"
        elif sandbox.status == "timeout":
            status = "timeout"
        else:
            status = "error"
        outcome = TestOutcome(status=status, output_excerpt=(sandbox.stdout + sandbox.stderr)[:8000])
        return ExecutionResult(status="completed" if status == "passed" else "failed", patch=patch,
                               changed_files=changed, test_outcome=outcome,
                               reasoner_id=type(self._reasoner).__name__)
