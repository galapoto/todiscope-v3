from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: tuple[str, ...]

