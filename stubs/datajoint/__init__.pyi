from collections import UserList
from collections.abc import Mapping, MutableMapping
from typing import Any, ContextManager, Iterable, Literal, Optional, TypedDict, TypeVar

PrimaryKey = Mapping[str, str | int | float]

class Table:
    @property
    def table_name(self) -> str: ...
    @property
    def full_table_name(self) -> str: ...
    @property
    def connection(self) -> Connection: ...
    @property
    def heading(self) -> Heading: ...
    def children(self, *, as_objects: Literal[True]) -> list[Table]: ...
    def describe(self, *, printout: bool = ...) -> str: ...
    def insert(self, rows: Iterable[Mapping[str, Any]]) -> None: ...
    def fetch(self, *, as_dict: Literal[True], download_path: str = ...) -> list[dict[str, Any]]: ...
    def delete(self) -> None: ...
    def delete_quick(self) -> None: ...
    def proj(self, *attributes: str) -> Table: ...
    def __and__(self: _T, condition: str | PrimaryKey | Iterable[PrimaryKey] | Table) -> _T: ...

class Heading: ...

_T = TypeVar("_T", bound=Table)

class Part: ...
class Computed: ...
class Imported: ...
class Lookup: ...
class Manual: ...

class ConnectionInfo(TypedDict):
    host: str
    user: str
    passwd: str

class Connection:
    conn_info: ConnectionInfo
    def __init__(self, host: str, user: str, password: str) -> None: ...
    @property
    def transaction(self) -> ContextManager[Connection]: ...

class Schema:
    database: str
    connection: Connection
    def __init__(self, schema_name: str, *, connection: Optional[Connection] = ...) -> None: ...
    def __call__(self, cls: type[Table], *, context: Optional[Mapping[str, Table]]) -> type[Table]: ...
    def spawn_missing_classes(self, context: Optional[MutableMapping[str, type[Table]]] = ...) -> None: ...

class AndList(UserList[Any]): ...

Configuration = TypedDict("Configuration", {"database.host": str, "database.user": str, "database.password": str})

config: Configuration
