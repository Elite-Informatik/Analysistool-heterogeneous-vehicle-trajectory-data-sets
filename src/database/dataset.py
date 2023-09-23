from typing import Optional, List
from uuid import uuid4, UUID

import pandas
from pandas import DataFrame
from sqlalchemy import Connection
from sqlalchemy.exc import SQLAlchemyError

from src.data_transfer.content.error import ErrorMessage
from src.data_transfer.exception.custom_exception import DatabaseConnectionError, InvalidUUID
from src.data_transfer.record import DatasetRecord, DataRecord, ErrorRecord
from src.database import dataset_meta_table
from src.database.data_provider import DataProvider
from src.database.database_connection import DatabaseConnection
from src.database.database_component import DatabaseComponent, UUID_COLUMN_NAME
from src.database.dataset_meta_table import DatasetMetaTable, META_TABLE_COLUMNS
from src.database.sql_querys import SQLQueries


class Dataset(DatabaseComponent):
    """
    It represents a dataset in the database. It contains the metadata of the dataset and the connection to the database.
    """

    def __init__(self, name: str, size: int, connection: DatabaseConnection, meta_table: DatasetMetaTable,
                 uuid: UUID = uuid4()):
        super().__init__(database_connection=connection)
        self._name: str = name
        self._size: int = size
        self._uuid: UUID = uuid
        self.data_table_name: str = connection.data_table
        self.meta_table = meta_table
        self.add_error_handler(self.meta_table)
        meta_table.add_table(dataset_name=name, dataset_uuid=uuid, dataset_size=size)

    def to_dataset_record(self) -> DatasetRecord:
        """
        gets the metadata of the dataset as a dataset record
        :return the dataset record
        """
        return DatasetRecord(self._name, self._size)

    def get_data_provider(self) -> DataProvider:
        """
        Gets the DataProvider instance initialized with the connection to the database and set to the current dataset.
        """

        return DataProvider(dataset_uuids=[self._uuid], connection=self.database_connection)

    def add_data(self, data: DataRecord) -> bool:
        """
        Adds the given data to the dataset.
        :param data: the data that will be added to the dataset as a DataRecord.
        """
        connection: Connection = self.get_connection()
        if connection is None:
            return False

        dataframe: DataFrame = data.data
        dataframe[UUID_COLUMN_NAME] = self._uuid

        dataframe.to_sql(name=self._name, con=connection, if_exists="append", index=False)
        self.database_connection.post_connection()
        return True

    def delete_dataset(self) -> bool:
        """
        Deletes the dataset from the database.
        """
        connection: Connection = self.get_connection()
        if connection is None:
            return False

        query: str = SQLQueries.DELETE_DATASET.value.format(table_name=self.data_table_name,
                                                            column=UUID_COLUMN_NAME,
                                                            uuid=self._uuid)

        query_successful: bool = self.query_sql(sql_query=query, connection=connection, read=False) is not None
        self.database_connection.post_connection()
        if not query_successful:
            return False
        delete_successful: bool = self.meta_table.remove_dataset(dataset_uuid=self._uuid)
        return delete_successful

    @classmethod
    def load_from_database(cls, database_connection: DatabaseConnection, meta_table: DatasetMetaTable,
                           uuid: UUID) -> "Dataset":
        """
        Loads a dataset from the database with the given uuid.
        :param database_connection: the database connection as a DatabaseConnection object
        :param meta_table: the meta table as a DatasetMetaTable object.
        :param uuid: the uuid of the dataset that will be loaded
        :return: the loaded dataset. If the dataset does not exist, an invalid dataset will be returned.
        """
        dataset: Dataset = cls(name="invalid", size=-1, connection=database_connection, meta_table=meta_table,
                               uuid=uuid)

        meta_data: DataFrame = dataset.meta_table.get_meta_data(dataset_uuid=uuid)

        if meta_data is None:
            dataset.throw_error(ErrorMessage.DATASET_LOAD_ERROR, "with uuid " + str(uuid))
            return dataset

        dataset._name = meta_data[META_TABLE_COLUMNS[0]][0]
        dataset._size = meta_data[META_TABLE_COLUMNS[2]][0]
        dataset._uuid = meta_data[META_TABLE_COLUMNS[1]][0]

        return dataset

    @property
    def uuid(self) -> UUID:
        """
        gets the identifier of the dataset
        :return: the identifier
        """
        return self._uuid

    @property
    def name(self) -> str:
        """
        gets the name of the dataset
        :return: the name
        """
        return self._name

    @property
    def size(self) -> int:
        """
        gets the size of the dataset
        :return: the size
        """
        return self._size