"""Intentional failing probe used once to prove the CI gate rejects failures."""


def test_ci_gate_probe() -> None:
    assert False, "intentional CI gate probe"
