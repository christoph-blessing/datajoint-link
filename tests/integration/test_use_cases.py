from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Generic, TypeVar

from dj_link.domain.custom_types import Identifier
from dj_link.domain.link import Link, create_link
from dj_link.domain.state import Commands, Components, Operations, Processes, Update, states
from dj_link.service.gateway import LinkGateway
from dj_link.service.use_cases import (
    DeleteRequestModel,
    ListIdleEntitiesRequestModel,
    ListIdleEntitiesResponseModel,
    OperationResponse,
    ProcessRequestModel,
    PullRequestModel,
    ResponseModel,
    delete,
    list_idle_entities,
    process,
    pull,
)
from tests.assignments import create_assignments, create_identifier, create_identifiers


class FakeLinkGateway(LinkGateway):
    def __init__(
        self,
        assignments: Mapping[Components, Iterable[Identifier]],
        *,
        tainted_identifiers: Iterable[Identifier] | None = None,
        processes: Mapping[Processes, Iterable[Identifier]] | None = None,
    ) -> None:
        self.assignments = {component: set(identifiers) for component, identifiers in assignments.items()}
        self.tainted_identifiers = set(tainted_identifiers) if tainted_identifiers is not None else set()
        if processes is None:
            self.processes: dict[Processes, set[Identifier]] = defaultdict(set)
        else:
            self.processes = {process: set(identifiers) for process, identifiers in processes.items()}

    def create_link(self) -> Link:
        return create_link(self.assignments, tainted_identifiers=self.tainted_identifiers, processes=self.processes)

    def apply(self, updates: Iterable[Update]) -> None:
        for update in updates:
            if update.command is Commands.START_PULL_PROCESS:
                self.processes[Processes.PULL].add(update.identifier)
                self.assignments[Components.OUTBOUND].add(update.identifier)
            if update.command is Commands.ADD_TO_LOCAL:
                self.assignments[Components.LOCAL].add(update.identifier)
            if update.command is Commands.FINISH_PULL_PROCESS:
                self.processes[Processes.PULL].remove(update.identifier)
            if update.command is Commands.START_DELETE_PROCESS:
                self.processes[Processes.DELETE].add(update.identifier)
            if update.command is Commands.REMOVE_FROM_LOCAL:
                self.assignments[Components.LOCAL].remove(update.identifier)
            if update.command is Commands.FINISH_DELETE_PROCESS:
                self.processes[Processes.DELETE].remove(update.identifier)
                self.assignments[Components.OUTBOUND].remove(update.identifier)
            if update.command is Commands.DEPRECATE:
                try:
                    self.processes[Processes.DELETE].remove(update.identifier)
                except KeyError:
                    self.processes[Processes.PULL].remove(update.identifier)


T = TypeVar("T", bound=ResponseModel)


class FakeOutputPort(Generic[T]):
    def __init__(self) -> None:
        self._response: T | None = None

    @property
    def response(self) -> T:
        assert self._response is not None
        return self._response

    def __call__(self, response: T) -> None:
        self._response = response


def test_pull_process_gets_started_when_idle_entity_gets_pulled() -> None:
    gateway = FakeLinkGateway(create_assignments({Components.SOURCE: {"1"}}))
    pull(
        PullRequestModel(frozenset(create_identifiers("1"))),
        link_gateway=gateway,
        output_port=FakeOutputPort[OperationResponse](),
    )
    entity = next(entity for entity in gateway.create_link() if entity.identifier == create_identifier("1"))
    assert entity.state is states.Activated


def test_correct_response_model_gets_passed_to_pull_output_port() -> None:
    gateway = FakeLinkGateway(create_assignments({Components.SOURCE: {"1"}}))
    output_port = FakeOutputPort[OperationResponse]()
    pull(
        PullRequestModel(frozenset(create_identifiers("1"))),
        link_gateway=gateway,
        output_port=output_port,
    )
    assert output_port.response.requested == create_identifiers("1")
    assert output_port.response.operation is Operations.PULL


def test_delete_process_is_started_when_pulled_entity_is_deleted() -> None:
    gateway = FakeLinkGateway(
        create_assignments({Components.SOURCE: {"1"}, Components.OUTBOUND: {"1"}, Components.LOCAL: {"1"}})
    )
    delete(
        DeleteRequestModel(frozenset(create_identifiers("1"))),
        link_gateway=gateway,
        output_port=FakeOutputPort[OperationResponse](),
    )
    entity = next(entity for entity in gateway.create_link() if entity.identifier == create_identifier("1"))
    assert entity.state is states.Received


def test_correct_response_model_gets_passed_to_delete_output_port() -> None:
    gateway = FakeLinkGateway(
        create_assignments({Components.SOURCE: {"1"}, Components.OUTBOUND: {"1"}, Components.LOCAL: {"1"}})
    )
    output_port = FakeOutputPort[OperationResponse]()
    delete(
        DeleteRequestModel(frozenset(create_identifiers("1"))),
        link_gateway=gateway,
        output_port=output_port,
    )
    assert output_port.response.requested == create_identifiers("1")
    assert output_port.response.operation is Operations.DELETE


def test_entity_undergoing_process_gets_processed() -> None:
    gateway = FakeLinkGateway(
        create_assignments({Components.SOURCE: {"1"}, Components.OUTBOUND: {"1"}}),
        processes={Processes.PULL: create_identifiers("1")},
    )
    process(
        ProcessRequestModel(frozenset(create_identifiers("1"))),
        link_gateway=gateway,
        output_port=FakeOutputPort[OperationResponse](),
    )
    entity = next(entity for entity in gateway.create_link() if entity.identifier == create_identifier("1"))
    assert entity.state is states.Received


def test_correct_response_model_gets_passed_to_process_output_port() -> None:
    gateway = FakeLinkGateway(
        create_assignments({Components.SOURCE: {"1"}, Components.OUTBOUND: {"1"}}),
        processes={Processes.PULL: create_identifiers("1")},
    )
    output_port = FakeOutputPort[OperationResponse]()
    process(
        ProcessRequestModel(frozenset(create_identifiers("1"))),
        link_gateway=gateway,
        output_port=output_port,
    )
    assert output_port.response.requested == create_identifiers("1")
    assert output_port.response.operation is Operations.PROCESS


def test_correct_response_model_gets_passed_to_list_idle_entities_output_port() -> None:
    link_gateway = FakeLinkGateway(
        create_assignments({Components.SOURCE: {"1", "2"}, Components.OUTBOUND: {"2"}, Components.LOCAL: {"2"}})
    )
    output_port = FakeOutputPort[ListIdleEntitiesResponseModel]()
    list_idle_entities(ListIdleEntitiesRequestModel(), link_gateway=link_gateway, output_port=output_port)
    assert set(output_port.response.identifiers) == create_identifiers("1")
