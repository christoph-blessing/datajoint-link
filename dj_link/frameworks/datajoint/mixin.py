"""Contains mixins that add functionality to DataJoint tables."""
from typing import Type

from datajoint import AndList
from datajoint.user_tables import UserTable

from ...adapters.datajoint.controller import Controller
from .factory import TableFactory
from .file import ReusableTemporaryDirectory
from .printer import Printer


class LocalTableMixin:
    """Mixin class for adding additional functionality to the local table class."""

    _controller: Controller
    _temp_dir: ReusableTemporaryDirectory
    _source_table_factory: TableFactory
    _printer: Printer
    restriction: AndList

    def pull(self, *restrictions) -> None:
        """Pull entities present in the (restricted) source table into the local table."""
        if not restrictions:
            restrictions = AndList()
        with self._temp_dir:
            self._controller.pull(restrictions)
        self._printer()

    def delete(self):
        """Delete entities from the local table."""
        self._controller.delete(self.restriction)
        self._printer()

    def refresh(self):
        """Refresh the repositories."""
        self._controller.refresh()
        self._printer()

    @property
    def source(self) -> Type[UserTable]:
        """Return the source table class."""
        return self._source_table_factory()
