"""Contains all the services."""
from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto

from link.domain import commands, events

from .uow import UnitOfWork


def pull(command: commands.PullEntities, *, uow: UnitOfWork) -> None:
    """Pull entities across the link."""
    with uow:
        uow.link.pull(command.requested)
        uow.commit()


def delete(command: commands.DeleteEntities, *, uow: UnitOfWork) -> None:
    """Delete pulled entities."""
    with uow:
        uow.link.delete(command.requested)
        uow.commit()


def list_idle_entities(
    command: commands.ListIdleEntities,
    *,
    uow: UnitOfWork,
    output_port: Callable[[events.IdleEntitiesListed], None],
) -> None:
    """List all idle entities."""
    with uow:
        uow.link.list_idle_entities()
        event = uow.link.events[-1]
        assert isinstance(event, events.IdleEntitiesListed)
        output_port(event)


class Services(Enum):
    """Names for all available services."""

    PULL = auto()
    DELETE = auto()
    LIST_IDLE_ENTITIES = auto()
