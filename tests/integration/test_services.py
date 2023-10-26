from __future__ import annotations

from functools import partial
from typing import Any, Callable, Generic, Protocol, TypedDict, TypeVar

import pytest

from link.domain import commands, events
from link.domain.state import Components, Operations, Processes, State, states
from link.service.services import delete, list_idle_entities, pull
from link.service.uow import UnitOfWork
from tests.assignments import create_assignments, create_identifier, create_identifiers

from .gateway import FakeLinkGateway

T = TypeVar("T", bound=events.Event)


class FakeOutputPort(Generic[T]):
    def __init__(self) -> None:
        self._response: T | None = None

    @property
    def response(self) -> T:
        assert self._response is not None
        return self._response

    def __call__(self, response: T) -> None:
        self._response = response


def create_uow(state: type[State], process: Processes | None = None, is_tainted: bool = False) -> UnitOfWork:
    if state in (states.Activated, states.Received):
        assert process is not None
    else:
        assert process is None
    if state in (states.Tainted, states.Deprecated):
        assert is_tainted
    elif state in (states.Idle, states.Pulled):
        assert not is_tainted

    if is_tainted:
        tainted_identifiers = create_identifiers("1")
    else:
        tainted_identifiers = set()
    if process is not None:
        processes = {process: create_identifiers("1")}
    else:
        processes = {}
    assignments = {Components.SOURCE: {"1"}}
    if state is states.Idle:
        return UnitOfWork(
            FakeLinkGateway(
                create_assignments(assignments), tainted_identifiers=tainted_identifiers, processes=processes
            )
        )
    assignments[Components.OUTBOUND] = {"1"}
    if state in (states.Deprecated, states.Activated):
        return UnitOfWork(
            FakeLinkGateway(
                create_assignments(assignments), tainted_identifiers=tainted_identifiers, processes=processes
            )
        )
    assignments[Components.LOCAL] = {"1"}
    return UnitOfWork(
        FakeLinkGateway(create_assignments(assignments), tainted_identifiers=tainted_identifiers, processes=processes)
    )


_Event_co = TypeVar("_Event_co", bound=events.Event, covariant=True)

_Command_contra = TypeVar("_Command_contra", bound=commands.Command, contravariant=True)


class Service(Protocol[_Command_contra, _Event_co]):
    """Protocol for services."""

    def __call__(self, command: _Command_contra, *, output_port: Callable[[_Event_co], None], **kwargs: Any) -> None:
        """Execute the service."""


def create_pull_service(uow: UnitOfWork) -> Service[commands.PullEntities, events.EntitiesPulled]:
    return partial(pull, uow=uow)


def create_delete_service(uow: UnitOfWork) -> Service[commands.DeleteEntities, events.EntitiesDeleted]:
    return partial(delete, uow=uow)


class EntityConfig(TypedDict):
    state: type[State]
    is_tainted: bool
    process: Processes | None


STATES: list[EntityConfig] = [
    {"state": states.Idle, "is_tainted": False, "process": None},
    {"state": states.Activated, "is_tainted": False, "process": Processes.PULL},
    {"state": states.Activated, "is_tainted": False, "process": Processes.DELETE},
    {"state": states.Activated, "is_tainted": True, "process": Processes.PULL},
    {"state": states.Activated, "is_tainted": True, "process": Processes.DELETE},
    {"state": states.Received, "is_tainted": False, "process": Processes.PULL},
    {"state": states.Received, "is_tainted": False, "process": Processes.DELETE},
    {"state": states.Received, "is_tainted": True, "process": Processes.PULL},
    {"state": states.Received, "is_tainted": True, "process": Processes.DELETE},
    {"state": states.Pulled, "is_tainted": False, "process": None},
    {"state": states.Tainted, "is_tainted": True, "process": None},
    {"state": states.Deprecated, "is_tainted": True, "process": None},
]


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (STATES[0], states.Idle),
        (STATES[1], states.Idle),
        (STATES[2], states.Idle),
        (STATES[3], states.Deprecated),
        (STATES[4], states.Deprecated),
        (STATES[5], states.Idle),
        (STATES[6], states.Idle),
        (STATES[7], states.Deprecated),
        (STATES[8], states.Deprecated),
        (STATES[9], states.Idle),
        (STATES[10], states.Deprecated),
        (STATES[11], states.Deprecated),
    ],
)
def test_deleted_entity_ends_in_correct_state(state: EntityConfig, expected: type[State]) -> None:
    uow = create_uow(**state)
    delete_service = create_delete_service(uow)
    delete_service(commands.DeleteEntities(frozenset(create_identifiers("1"))), output_port=lambda x: None)
    with uow:
        assert next(iter(uow.link)).state is expected


def test_correct_response_model_gets_passed_to_delete_output_port() -> None:
    uow = UnitOfWork(
        FakeLinkGateway(
            create_assignments({Components.SOURCE: {"1"}, Components.OUTBOUND: {"1"}, Components.LOCAL: {"1"}})
        )
    )
    output_port = FakeOutputPort[events.EntitiesDeleted]()
    delete_service = create_delete_service(uow)
    delete_service(commands.DeleteEntities(frozenset(create_identifiers("1"))), output_port=output_port)
    assert output_port.response.requested == create_identifiers("1")


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (STATES[0], states.Pulled),
        (STATES[1], states.Pulled),
        (STATES[2], states.Pulled),
        (STATES[3], states.Deprecated),
        (STATES[4], states.Deprecated),
        (STATES[5], states.Pulled),
        (STATES[6], states.Pulled),
        (STATES[7], states.Tainted),
        (STATES[8], states.Deprecated),
        (STATES[9], states.Pulled),
        (STATES[10], states.Tainted),
        (STATES[11], states.Deprecated),
    ],
)
def test_pulled_entity_ends_in_correct_state(state: EntityConfig, expected: type[State]) -> None:
    uow = create_uow(**state)
    pull_service = create_pull_service(uow)
    pull_service(
        commands.PullEntities(frozenset(create_identifiers("1"))),
        output_port=lambda x: None,
    )
    with uow:
        assert next(iter(uow.link)).state is expected


@pytest.mark.parametrize(
    ("state", "produces_error"),
    [
        (STATES[0], False),
        (STATES[1], False),
        (STATES[2], False),
        (STATES[3], True),
        (STATES[4], True),
        (STATES[5], False),
        (STATES[6], False),
        (STATES[7], False),
        (STATES[8], True),
        (STATES[9], False),
        (STATES[10], False),
        (STATES[11], True),
    ],
)
def test_correct_response_model_gets_passed_to_pull_output_port(state: EntityConfig, produces_error: bool) -> None:
    if produces_error:
        errors = {
            events.InvalidOperationRequested(
                operation=Operations.START_PULL, identifier=create_identifier("1"), state=states.Deprecated
            )
        }
    else:
        errors = set()
    gateway = create_uow(**state)
    output_port = FakeOutputPort[events.EntitiesPulled]()
    pull_service = create_pull_service(gateway)
    pull_service(
        commands.PullEntities(frozenset(create_identifiers("1"))),
        output_port=output_port,
    )
    assert output_port.response == events.EntitiesPulled(
        requested=frozenset(create_identifiers("1")), errors=frozenset(errors)
    )


def test_correct_response_model_gets_passed_to_list_idle_entities_output_port() -> None:
    uow = UnitOfWork(
        FakeLinkGateway(
            create_assignments({Components.SOURCE: {"1", "2"}, Components.OUTBOUND: {"2"}, Components.LOCAL: {"2"}})
        )
    )
    output_port = FakeOutputPort[events.IdleEntitiesListed]()
    list_idle_entities(commands.ListIdleEntities(), uow=uow, output_port=output_port)
    assert set(output_port.response.identifiers) == create_identifiers("1")
