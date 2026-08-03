"""Deterministic line-preserving text chunking."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    content: str
    start_line: int
    end_line: int


def chunk_text(raw_text: str, *, max_lines: int = 200, max_chars: int = 4000) -> list[TextChunk]:
    """Split text without crossing exact line or character bounds."""
    if max_lines < 1 or max_chars < 1:
        raise ValueError("chunk bounds must be positive")
    lines = raw_text.splitlines(keepends=True)
    if not lines and raw_text:
        lines = [raw_text]
    chunks: list[TextChunk] = []
    current: list[str] = []
    start = 1
    size = 0
    for line_no, line in enumerate(lines, 1):
        # Preserve every character even when one physical line exceeds max_chars.
        pieces = [line[i:i + max_chars] for i in range(0, len(line), max_chars)] or [""]
        for piece_index, piece in enumerate(pieces):
            if current and (len(current) >= max_lines or size + len(piece) > max_chars):
                chunks.append(TextChunk("".join(current), start, line_no - (1 if piece_index == 0 else 0)))
                current, size, start = [], 0, line_no
            current.append(piece)
            size += len(piece)
            if len(pieces) > 1 and piece_index < len(pieces) - 1:
                chunks.append(TextChunk("".join(current), start, line_no))
                current, size, start = [], 0, line_no
    if current:
        chunks.append(TextChunk("".join(current), start, len(lines)))
    return chunks
