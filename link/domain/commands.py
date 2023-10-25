"""Contains all domain commands."""
from __future__ import annotations

from dataclasses import dataclass

from .custom_types import Identifier


@dataclass(frozen=True)
class Command:
    """Base class for all commands."""


@dataclass(frozen=True)
class ProcessLink(Command):
    """Process the requested entities in the link."""

    requested: frozenset[Identifier]
