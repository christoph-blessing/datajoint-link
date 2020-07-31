from unittest.mock import MagicMock, call

import pytest

from link.entities.abstract_gateway import AbstractGateway
from link.base import Base
from link.adapters.datajoint.gateway import DataJointGateway
from link.adapters.datajoint.abstract_facade import AbstractTableFacade
from link.adapters.datajoint.identification import IdentificationTranslator


def test_if_datajoint_gateway_is_subclass_of_abstract_gateway():
    assert issubclass(DataJointGateway, AbstractGateway)


@pytest.fixture
def primary_keys():
    return ["primary_key" + str(i) for i in range(3)]


@pytest.fixture
def flags():
    return dict(SuperLongAndComplexFlag=True, AnotherEvenLongerAndMoreComplexFlag=False)


@pytest.fixture
def table_facade_spy(primary_keys, flags):
    table_facade_spy = MagicMock(name="table_facade_spy", spec=AbstractTableFacade, primary_keys=primary_keys)
    table_facade_spy.get_primary_keys_in_restriction.return_value = primary_keys
    table_facade_spy.get_flags.return_value = flags
    table_facade_spy.fetch_master.return_value = "master_entity"
    table_facade_spy.fetch_parts.return_value = "part_entities"
    return table_facade_spy


@pytest.fixture
def identifiers():
    return ["identifier" + str(i) for i in range(3)]


@pytest.fixture
def translator_spy(identifiers):
    translator_spy = MagicMock(name="translator_spy", spec=IdentificationTranslator)
    translator_spy.to_identifier.side_effect = identifiers
    translator_spy.to_primary_key.return_value = "primary_key0"
    return translator_spy


@pytest.fixture
def gateway(table_facade_spy, translator_spy):
    return DataJointGateway(table_facade_spy, translator_spy)


def test_if_gateway_is_subclass_of_base():
    assert issubclass(DataJointGateway, Base)


class TestInit:
    def test_if_table_facade_is_stored_as_instance_attribute(self, gateway, table_facade_spy):
        assert gateway.table_facade is table_facade_spy

    def test_if_translator_is_stored_as_instance_attribute(self, gateway, translator_spy):
        assert gateway.translator is translator_spy


class TestIdentifiersProperty:
    def test_if_call_to_translator_is_correct(self, gateway, translator_spy, primary_keys):
        _ = gateway.identifiers
        assert translator_spy.to_identifier.call_args_list == [call(primary_key) for primary_key in primary_keys]

    def test_if_identifiers_are_returned(self, gateway, identifiers):
        assert gateway.identifiers == identifiers


class TestGetIdentifiersInRestriction:
    @pytest.fixture
    def restriction(self):
        return "restriction"

    def test_if_call_to_get_primary_keys_in_restriction_method_in_table_facade_is_correct(
        self, gateway, table_facade_spy, restriction
    ):
        gateway.get_identifiers_in_restriction(restriction)
        table_facade_spy.get_primary_keys_in_restriction.assert_called_once_with(restriction)

    def test_if_call_to_translator_is_correct(self, gateway, translator_spy, primary_keys, restriction):
        gateway.get_identifiers_in_restriction(restriction)
        assert translator_spy.to_identifier.call_args_list == [call(primary_key) for primary_key in primary_keys]

    def test_if_identifiers_in_restriction_are_returned(self, gateway, identifiers, restriction):
        assert gateway.get_identifiers_in_restriction(restriction) == identifiers


class TestGetFlags:
    def test_if_call_to_translator_is_correct(self, gateway, translator_spy):
        gateway.get_flags("identifier0")
        translator_spy.to_primary_key.assert_called_once_with("identifier0")

    def test_if_call_to_table_facade_is_correct(self, gateway, table_facade_spy):
        gateway.get_flags("identifier0")
        table_facade_spy.get_flags.assert_called_once_with("primary_key0")

    def test_if_correct_flags_are_returned(self, gateway):
        flags = dict(super_long_and_complex_flag=True, another_even_longer_and_more_complex_flag=False)
        assert gateway.get_flags("identifier0") == flags


class TestFetch:
    def test_if_call_to_translator_is_correct(self, gateway, translator_spy):
        gateway.fetch("identifier0")
        translator_spy.to_primary_key.assert_called_once_with("identifier0")

    def test_if_call_to_fetch_master_method_of_table_facade_is_correct(self, gateway, table_facade_spy):
        gateway.fetch("identifier0")
        table_facade_spy.fetch_master.assert_called_once_with("primary_key0")

    def test_if_call_to_fetch_parts_method_of_table_facade_is_correct(self, gateway, table_facade_spy):
        gateway.fetch("identifier0")
        table_facade_spy.fetch_parts.assert_called_once_with("primary_key0")

    def test_if_returned_data_is_correct(self, gateway):
        assert gateway.fetch("identifier0") == dict(master="master_entity", parts="part_entities")


@pytest.fixture
def data():
    return dict(master="master_entity", parts="part_entities")


class TestInsert:
    def test_if_master_entity_is_inserted_into_proxy(self, gateway, table_facade_spy, data):
        gateway.insert(data)
        table_facade_spy.insert_master.assert_called_once_with(data["master"])

    def test_if_part_entities_are_inserted_into_proxy(self, gateway, table_facade_spy, data):
        gateway.insert(data)
        table_facade_spy.insert_parts.assert_called_once_with(data["parts"])

    def test_if_master_entity_is_inserted_before_part_entities_are(self, gateway, table_facade_spy, data):
        table_facade_spy.insert_master.side_effect = RuntimeError
        try:
            gateway.insert(data)
        except RuntimeError:
            pass
        table_facade_spy.insert_parts.assert_not_called()


class TestDelete:
    def test_if_call_to_translator_is_correct(self, gateway, translator_spy):
        gateway.delete("identifier0")
        translator_spy.to_primary_key.assert_called_once_with("identifier0")

    def test_if_call_to_delete_parts_method_of_table_facade_is_correct(self, gateway, table_facade_spy):
        gateway.delete("identifier0")
        table_facade_spy.delete_parts.assert_called_once_with("primary_key0")

    def test_if_call_to_delete_master_method_of_table_facade_is_correct(self, gateway, table_facade_spy):
        gateway.delete("identifier0")
        table_facade_spy.delete_master.assert_called_once_with("primary_key0")

    def test_if_call_to_delete_parts_method_is_made_first(self, gateway, table_facade_spy):
        table_facade_spy.delete_parts.side_effect = RuntimeError
        try:
            gateway.delete("identifier0")
        except RuntimeError:
            pass
        table_facade_spy.delete_master.assert_not_called()


class TestSetFlag:
    @pytest.fixture
    def flag_name(self):
        return "my_awesome_flag"

    @pytest.fixture(params=[True, False])
    def flag_value(self, request):
        return request.param

    @pytest.fixture(autouse=True)
    def set_flag(self, gateway, flag_name, flag_value):
        gateway.set_flag("identifier0", flag_name, flag_value)

    @pytest.fixture
    def called_method(self, flag_value):
        if flag_value:
            return "enable_flag"
        else:
            return "disable_flag"

    def test_if_call_to_translator_is_correct(self, translator_spy):
        translator_spy.to_primary_key.assert_called_once_with("identifier0")

    def test_if_call_to_table_facade_is_correct(self, table_facade_spy, called_method):
        getattr(table_facade_spy, called_method).assert_called_once_with("primary_key0", "MyAwesomeFlag")


def test_if_transaction_is_started_in_proxy(gateway, table_facade_spy):
    gateway.start_transaction()
    table_facade_spy.start_transaction.assert_called_once_with()


def test_if_transaction_is_committed_in_proxy(gateway, table_facade_spy):
    gateway.commit_transaction()
    table_facade_spy.commit_transaction.assert_called_once_with()


def test_if_transaction_is_cancelled_in_proxy(gateway, table_facade_spy):
    gateway.cancel_transaction()
    table_facade_spy.cancel_transaction.assert_called_once_with()
