"""Provider-free deterministic embedding used to prove the M2 mechanism."""

from hashlib import sha256
import math
import re
from typing import Protocol


class Embedder(Protocol):
    def embed(self, text: str) -> tuple[float, ...]: ...


class DeterministicHashEmbedder:
    def __init__(self, dimension: int = 32) -> None:
        if dimension < 1:
            raise ValueError("dimension must be positive")
        self.dimension = dimension

    def embed(self, text: str) -> tuple[float, ...]:
        values = [0.0] * self.dimension
        for token in re.findall(r"\w+", text.casefold()):
            digest = sha256(token.encode("utf-8")).digest()
            values[int.from_bytes(digest[:4], "big") % self.dimension] += 1.0
        norm = math.sqrt(sum(value * value for value in values))
        return tuple(value / norm for value in values) if norm else tuple(values)
