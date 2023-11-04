from abc import ABC
from typing import List, Optional, Dict
from uuid import UUID

from pandas import DataFrame

from src.data_transfer.content import Column
from src.data_transfer.content.error import ErrorMessage
from src.data_transfer.exception.custom_exception import DatabaseConnectionError
from src.data_transfer.record import DataRecord, DatasetRecord
from src.database.data_facade import DataFacade
from src.database.data_provider import DataProvider
from src.database.database_connection import DatabaseConnection
from src.database.dataset import Dataset, INVALID_NAME
from src.database.dataset_facade import DatasetFacade
from src.database.dataset_meta_table import DatasetMetaTable
from src.database.idatabase import IDatabase

REQUIRED_CONNECTION_KEYS = ["host",
                            "user",
                            "password",
                            "database",
                            "port",
                            "data_table",
                            "meta_table"]


class Database(IDatabase, DatasetFacade):
    """
    this interface represents a database
    """

    def __init__(self):
        super().__init__()
        self.meta_table: Optional[DatasetMetaTable] = None
        self.data_provider: Optional[DataProvider] = None
        self.active_datasets: List[Dataset] = []
        self.connection: Optional[DatabaseConnection] = None

    def load_dataset(self, dataset_uuid: UUID) -> bool:
        """
        Loads the dataset with the given uuid from the database. This means later requested data will be loaded from
        this dataset as well. If another dataset is already loaded it will be added to the list of current datasets.
        """
        self._assert_database_configured()

        dataset: Dataset = Dataset.load_from_database(database_connection=self.connection,
                                                      meta_table=self.meta_table, uuid=dataset_uuid)

        if dataset.name == INVALID_NAME:
            for error in dataset.errors:
                self.throw_error(error.error_type, error.args)
            return False

        self.add_error_handler(dataset)

    def get_active_datasets(self) -> List[UUID]:
        pass

    def get_data_sets_as_dict(self) -> Dict[str, int]:
        """
        Currently not implemented.
        """
        # todo: remove code. This method is not needed anymore.
        pass

    def set_data_sets_as_dict(self) -> List[UUID]:
        # todo: remove this method
        pass

    def set_connection(self, connection: Dict[str, str]) -> bool:
        """
        Sets the connection to the database using the given connection dict. Also creates the meta table.
        """
        assert self.connection is not None
        # assert that all necessary parameters are given in the connection dict
        if not all(key in connection.keys() for key in REQUIRED_CONNECTION_KEYS):
            raise KeyError(ErrorMessage.MISSING_CONNECTION_PARAMETER.value.format(expected=REQUIRED_CONNECTION_KEYS,
                                                                                  got=connection.keys()))
        try:
            self.connection = DatabaseConnection(host=connection["host"],
                                                 user=connection["user"],
                                                 password=connection["password"],
                                                 database=connection["database"],
                                                 port=connection["port"],
                                                 data_table=connection["data_table"],
                                                 meta_table=connection["meta_table"])
        except DatabaseConnectionError as e:
            self.throw_error(ErrorMessage.DATABASE_CONNECTION_ERROR, e.args[0])
            return False
        self.meta_table = DatasetMetaTable(self.connection)
        self.add_error_handler(self.meta_table)
        self.data_provider = DataProvider(connection=self.connection, dataset_facade=self, meta_table=self.meta_table)
        self.add_error_handler(self.data_provider)
        return True

    def get_data_set_meta(self, dataset_uuid: UUID) -> Optional[DatasetRecord]:
        return self.meta_table.get_meta_data_as_record(dataset_uuid)

    def delete_dataset(self, dataset_uuid: UUID) -> bool:
        pass

    def set_current_dataset(self, dataset_uuid: UUID, replace: bool = True) -> bool:
        """
        Sets the current dataset to the dataset with the given uuid.
        :param dataset_uuid: the uuid of the dataset as a UUID object
        :param replace: If the currently selected dataset should be replaced. Default is True
        :return: True if the dataset was set successfully, otherwise False
        :raises RuntimeError: if the connection to the database was not set before
        """

    def add_dataset(self, data: DataRecord, append: bool = False) -> Optional[UUID]:
        """
        Adds a new dataset to the database. If append is True, the data will be appended to the first dataset.
        :param data: the data that will be added as a DataRecord
        :param append: if the data should be appended to the first dataset. Default is False
        :return: the uuid of the newly added dataset as a UUID object if the dataset was added successfully, otherwise
                None
        """
        self._assert_database_configured()

        if append and len(self.active_datasets) == 0:
            raise RuntimeError(ErrorMessage.DATABASE_APPEND_TO_EMPTY.value)

        if append:
            dataset: Dataset = self.active_datasets[0]
        else:
            dataset: Dataset = Dataset(name=data.name, size=data.data.memory_usage(index=True).sum(),
                                       connection=self.connection, meta_table=self.meta_table)

        added_success: bool = dataset.add_data(data=data)
        if dataset.error_occured() or not added_success:
            errors = dataset.get_errors()
            for error in errors:
                self.throw_error(error.error_type, error.args)
            return None

        # if append is false the dataset is new
        # and thus needs to be added to the list of datasets and the error handlers
        if not append:
            self.active_datasets.append(dataset)
            self.add_error_handler(dataset)

        return dataset.uuid

    def unload_dataset(self, dataset_uuid: UUID) -> bool:
        """
        Closes the dataset with the given uuid. By closing a dataset, the dataset will be removed from the list of
        datasets and the error handlers.
        :param dataset_uuid: the uuid of the dataset that should be closed as a UUID object
        :return: True if the dataset was closed successfully, otherwise False
        :raises RuntimeError: if the dataset with the given uuid does not exist
        """
        self._assert_database_configured()

        for dataset in self.active_datasets:
            if dataset.uuid == dataset_uuid:
                self.active_datasets.remove(dataset)
                self.remove_error_handler(dataset)
                return True
        raise RuntimeError(ErrorMessage.DATASET_NOT_EXISTING.value + str(dataset_uuid))

    def table_exists(self, table_name: str) -> bool:
        return False # todo: remove relict, all datasets now have ids.

    @property
    def dataset_facade(self) -> DatasetFacade:
        return self

    @property
    def data_facade(self) -> DataFacade:
        """
        Returns the data facade used for accessing the data and applying filters.
        """
        return self.data_provider

    def _assert_database_configured(self) -> None:
        """
        Asserts that the database is configured.
        """
        if self.connection is None:
            raise RuntimeError(ErrorMessage.DATABASE_ACCESS_BEFORE_CONNECTION.value)
