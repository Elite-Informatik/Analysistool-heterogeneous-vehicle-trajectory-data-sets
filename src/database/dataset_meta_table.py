from typing import Optional, List

from pandas import DataFrame, Series
from sqlalchemy import text, TextClause, Connection
from uuid import UUID

from src.data_transfer.content.error import ErrorMessage
from src.data_transfer.exception.custom_exception import DatabaseConnectionError
from src.database.database_connection import DatabaseConnection
from src.database.database_component import DatabaseComponent
from src.database.sql_querys import SQLQueries

META_TABLE_COLUMNS: list = ["name", "dataset_id", "size"]
META_TABLE_NAME = 0
META_TABLE_UUID = 1
META_TABLE_SIZE = 2


class DatasetMetaTable(DatabaseComponent):
    """
    A class representing the table consisting of the meta information of the datasets.
    """
    _table_exists: bool = False

    def __init__(self, connection: DatabaseConnection):
        super().__init__(database_connection=connection)
        self.name = connection.meta_table
        if not DatasetMetaTable._table_exists and not self._exists():
            DatasetMetaTable._table_exists = self._create_table()

    def _exists(self) -> bool:
        """
        Checks if the meta_table already exists in the database.
        :return: True if the Table exists and False if it doesn't or an error occurred.
        """
        connection: Connection = self.get_connection()
        if connection is None:
            return False

        query: str = SQLQueries.GET_ALL_TABLES.value

        tables: DataFrame = self.query_sql(sql_query=query, connection=connection)

        return tables.isin([self.name]).any().any()

    def _create_table(self) -> bool:
        """
        Creates the meta_table in the database.
        :return: True if the table was created successfully and False if an error occurred.
        """
        connection: Connection = self.get_connection()
        if connection is None:
            return False

        query: str = SQLQueries.CREATE_TABLE.value.format(table_name=text(self.name),
                                                          columns=META_TABLE_COLUMNS[META_TABLE_NAME] + " TEXT, "
                                                                  + META_TABLE_COLUMNS[META_TABLE_UUID] + " TEXT, "
                                                                  + META_TABLE_COLUMNS[META_TABLE_SIZE] + " DOUBLE "
                                                                                                          "PRECISION")

        self.query_sql(sql_query=query, connection=connection, read=False)
        self.database_connection.post_connection()

        return True

    def add_table(self, dataset_name: str, dataset_uuid: UUID, dataset_size: int) -> bool:
        """
        Adds a table to the meta_table.
        :param dataset_name: The name of the dataset.
        :param dataset_uuid: The uuid of the dataset.
        :param dataset_size: The size of the dataset.
        """
        connection: Connection = self._assert_table_exists_get_connection()
        if connection is None:
            return False

        dataset_meta_data: DataFrame = DataFrame(data={META_TABLE_COLUMNS[META_TABLE_NAME]: [dataset_name],
                                                       META_TABLE_COLUMNS[META_TABLE_UUID]: [dataset_uuid],
                                                       META_TABLE_COLUMNS[META_TABLE_SIZE]: [dataset_size]})

        dataset_meta_data.to_sql(name=self.name, con=connection.engine, if_exists="append", index=False)
        self.database_connection.post_connection()

    def adjust_size(self, dataset_uuid: UUID, new_size: int) -> bool:
        """
        Adjusts the size of a dataset in the meta_table.
        :param dataset_uuid: The uuid of the dataset.
        :param new_size: The new size of the dataset.
        """
        connection: Connection = self._assert_table_exists_get_connection()
        if connection is None:
            return False

        query: str = SQLQueries.UPDATE_DATASET_SIZE.value.format(meta_table_name=self.name,
                                                                 column=META_TABLE_COLUMNS[META_TABLE_SIZE],
                                                                 uuid=dataset_uuid,
                                                                 new_size=new_size)

        self.query_sql(sql_query=query, connection=connection, read=False)
        self.database_connection.post_connection()

        return True

    def contains(self, dataset_uuid: UUID) -> bool:
        """
        Checks if the meta_table contains the meta dataset.
        :param dataset_uuid: The uuid of the dataset to check.
        """

        dataset_meta_data: Optional[DataFrame] = self.get_meta_data(dataset_uuid=dataset_uuid)

        return dataset_meta_data is not None

    def get_meta_data(self, dataset_uuid: UUID) -> Optional[DataFrame]:
        """
        Gets the metadata of a dataset as a Dataframe. Returns None if the connection to the database failed or if no
        dataset with the given uuid exists.

        :param dataset_uuid: The dataset to get the metadata of.
        :return: The metadata of the dataset as an optional Dataframe.
        :raises RuntimeError: If the database contains multiple datasets with the same uuid or if the column names of
        the returned Dataframe (from the database) are not the same as the expected ones.
        This would indicate a change in the database or an error in the code.
        """

        connection: Connection = self.get_connection()
        if connection is None:
            return None
        query: str = SQLQueries.SELECT_DATASET_METADATA.value.format(columns=f"{META_TABLE_COLUMNS[META_TABLE_NAME]}, "
                                                                             f"{META_TABLE_COLUMNS[META_TABLE_UUID]}, "
                                                                             f"{META_TABLE_COLUMNS[META_TABLE_SIZE]}",
                                                                     uuid=dataset_uuid,
                                                                     meta_table_name=self.name)

        dataset_meta_data: DataFrame = self.query_sql(sql_query=query, connection=connection)

        if dataset_meta_data is None or dataset_meta_data.empty:
            self.throw_error(ErrorMessage.DATASET_NOT_EXISTING, "uuid: " + str(dataset_uuid))
            return None

        if dataset_meta_data.shape[0] > 1:
            raise RuntimeError(ErrorMessage.DATABASE_MULTIPLE_DATASETS_WITH_SAME_UUID.value + " for uuid: " + str(
                dataset_uuid))
        dataset_columns: List[str] = list(dataset_meta_data.columns)

        if len(dataset_columns) != len(META_TABLE_COLUMNS) \
                or dataset_columns[0] != META_TABLE_COLUMNS[0] or dataset_columns[1] != META_TABLE_COLUMNS[1] \
                or dataset_columns[2] != META_TABLE_COLUMNS[2]:
            raise RuntimeError(ErrorMessage.DATABASE_WRONG_COLUMN_NAMES.value + "expected: " + str(
                META_TABLE_COLUMNS) + " got: " + str(dataset_columns))

        self.database_connection.post_connection()

        return dataset_meta_data

    def remove_dataset(self, dataset_uuid: UUID) -> bool:
        """
        Removes a dataset from the meta_table.
        """
        connection: Connection = self._assert_table_exists_get_connection()
        if connection is None:
            self.throw_error(ErrorMessage.DATASET_NOT_DELETED)
            return False

        query: str = SQLQueries.DELETE_DATASET.value.format(uuid=dataset_uuid,
                                                            table_name=self.name,
                                                            column=META_TABLE_COLUMNS[META_TABLE_UUID])

        self.query_sql(sql_query=query, connection=connection, read=False)
        self.database_connection.post_connection()

        return True

    def get_all_datasets(self) -> List[UUID]:
        """
        Gets the uuids of every dataset referenced the meta table.
        :returns: A list of UUIDs corresponding to the datasets in the meta table.
        """
        connection: Connection = self._assert_table_exists_get_connection()
        if connection is None:
            self.throw_error(ErrorMessage.ALL_DATASETS_LOAD_ERROR)
            return []
        query: str = SQLQueries.GET_COLUMN_FROM_TABLE.value.format(column=META_TABLE_COLUMNS[META_TABLE_UUID],
                                                                   table_name=self.name)

        uuid_dataframe: DataFrame = self.query_sql(sql_query=query, connection=connection)

        if uuid_dataframe is None:
            self.throw_error(ErrorMessage.ALL_DATASETS_LOAD_ERROR)
            return []

        columns: List[str] = list(uuid_dataframe.columns)
        # raises a RuntimeError as this should not be possible
        if len(columns) != 1 or META_TABLE_COLUMNS[1] not in columns:
            raise RuntimeError(f"The data loaded from the Database is not in the correct format. Expected: "
                               f"[{META_TABLE_COLUMNS[1]}], but got: {columns}")

        return uuid_dataframe[META_TABLE_COLUMNS[1]].to_list()

    def _assert_table_exists_get_connection(self) -> Optional[Connection]:
        """
        Checks if the meta table exists and returns the connection to the database.
        """
        if not self._table_exists:
            self.throw_error(ErrorMessage.META_TABLE_NOT_EXISTING, "There might be a problem with the database.")
            return None

        connection: Connection = self.get_connection()
        if connection is None:
            return None

        return connection