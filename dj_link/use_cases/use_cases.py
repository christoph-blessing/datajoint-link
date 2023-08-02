"""Contains all the use-cases."""
from __future__ import annotations

from dataclasses import dataclass

from dj_link.entities.custom_types import Identifier
from dj_link.entities.link import delete as delete_domain_service
from dj_link.entities.link import process
from dj_link.entities.link import pull as pull_domain_service

from .gateway import LinkGateway


@dataclass(frozen=True)
class PullRequestModel:
    """Request model for the pull use-case."""

    identifiers: frozenset[Identifier]


def pull(request: PullRequestModel, *, link_gateway: LinkGateway) -> None:
    """Pull entities across the link."""
    updates = pull_domain_service(link_gateway.create_link(), requested=request.identifiers)
    while any(update.is_state_changing for update in updates):
        link_gateway.apply(updates)
        updates = process(link_gateway.create_link())


@dataclass(frozen=True)
class DeleteRequestModel:
    """Request model for the delete use-case."""

    identifiers: frozenset[Identifier]


def delete(request: DeleteRequestModel, *, link_gateway: LinkGateway) -> None:
    """Delete pulled entities."""
    updates = delete_domain_service(link_gateway.create_link(), requested=request.identifiers)
    while any(update.is_state_changing for update in updates):
        link_gateway.apply(updates)
        updates = process(link_gateway.create_link())
