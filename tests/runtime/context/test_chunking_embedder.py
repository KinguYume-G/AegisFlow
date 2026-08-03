from math import isclose

from aegisflow_core.runtime.context.chunking import chunk_text
from aegisflow_core.runtime.context.embedder import DeterministicHashEmbedder


def test_chunking_preserves_content_and_exact_ranges() -> None:
    text = "".join(f"line {i}\n" for i in range(1, 402))
    chunks = chunk_text(text)
    assert "".join(chunk.content for chunk in chunks) == text
    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(1, 200), (201, 400), (401, 401)]


def test_hash_embedding_is_deterministic_normalized_and_handles_empty() -> None:
    embedder = DeterministicHashEmbedder()
    first = embedder.embed("Alpha beta alpha")
    assert first == embedder.embed("Alpha beta alpha")
    assert len(first) == 32
    assert isclose(sum(value * value for value in first), 1.0)
    assert embedder.embed("") == (0.0,) * 32
