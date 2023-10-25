"""Contains all domain commands."""
from __future__ import annotations

from dataclasses import dataclass

from .custom_types import Identifier


@dataclass(frozen=True)
class Command:
    """Base class for all commands."""


@dataclass(frozen=True)
class FullyProcessLink(Command):
    """Process the requested entities in the link until their processes are completed."""

    requested: frozenset[Identifier]


@dataclass(frozen=True)
class ProcessLink(Command):
    """Process the requested entities in the link."""

    requested: frozenset[Identifier]


@dataclass(frozen=True)
class StartPullProcess(Command):
    """Start the pull process for the requested entities."""

    requested: frozenset[Identifier]


@dataclass(frozen=True)
class StartDeleteProcess(Command):
    """Start the delete process for the requested entities."""

    requested: frozenset[Identifier]


@dataclass(frozen=True)
class ListIdleEntities(Command):
    """Start the delete process for the requested entities."""
