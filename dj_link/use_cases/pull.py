"""Contains code pertaining to the pull use-case."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Set

from ..entities.link import Identifier, Link, pull
from .base import AbstractRequestModel, AbstractResponseModel, AbstractUseCase

if TYPE_CHECKING:
    from . import RepositoryLink

LOGGER = logging.getLogger(__name__)


@dataclass
class PullRequestModel(AbstractRequestModel):
    """Request model for pull use-case."""

    identifiers: List[str]


@dataclass
class PullResponseModel(AbstractResponseModel):
    """Response model for the pull use-case."""

    requested: Set[str]
    valid: Set[str]
    invalid: Set[str]

    @property
    def n_requested(self) -> int:
        """Return the number of entities for which a pull was requested."""
        return len(self.requested)

    @property
    def n_valid(self) -> int:
        """Return the number of entities that were pulled."""
        return len(self.valid)

    @property
    def n_invalid(self) -> int:
        """Return the number of entities that were not pulled."""
        return len(self.invalid)


class PullUseCase(AbstractUseCase[PullRequestModel, PullResponseModel]):  # pylint: disable=too-few-public-methods
    """Use-case that pulls entities from the source to the local table."""

    name = "pull"
    response_model_cls = PullResponseModel

    def execute(self, repo_link: RepositoryLink, request_model: PullRequestModel) -> PullResponseModel:
        """Pull the entities specified by the provided identifiers if they were not already pulled."""
        valid_identifiers = {Identifier(i) for i in request_model.identifiers if i not in self.gateway_link.outbound}
        link = Link(
            source={Identifier(i) for i in self.gateway_link.source},
            outbound={Identifier(i) for i in self.gateway_link.outbound},
            local={Identifier(i) for i in self.gateway_link.local},
        )
        transfers = pull(link, requested=valid_identifiers)
        for transfer in transfers:
            self.gateway_link.transfer(transfer)
        return self.response_model_cls(
            requested=set(request_model.identifiers),
            valid={str(i) for i in valid_identifiers},
            invalid=set(request_model.identifiers) - valid_identifiers,
        )
