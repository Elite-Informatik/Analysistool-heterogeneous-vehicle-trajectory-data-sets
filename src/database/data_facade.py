from abc import abstractmethod
from typing import List
from typing import Optional

from src.data_transfer.content import Column
from src.data_transfer.record import DataRecord
from src.model.error_handler import ErrorHandler


class DataFacade(ErrorHandler):
    """
    DataFacade is interface for accessing Data in the Database.
    """

    @abstractmethod
    def set_point_filter(self, filter_str: str, use_filter: bool, negate_filter: bool) -> None:
        """
        Sets a point filter for the data points.
        :param filter_str: String representation of the filter.
        :param use_filter: Boolean indicating if the filter should be used.
        :param negate_filter: Boolean indicating if the filter should be _negated.
        """

    @abstractmethod
    def set_trajectory_filter(self, filter_str: str, use_filter: bool) -> None:
        """
        Sets a filter for the trajectorys.
        :param filter_str: String representation of the filter.
        :param use_filter: Boolean indicating if the filter should be used.
        """
        pass

    @abstractmethod
    def get_data(self, columns: List[Column]) -> Optional[DataRecord]:
        """
        Gets the data with specified columns.
        :param columns: List of Column objects specifying the columns to return.
        :return: DataRecord object with the requested data.
        """
        pass

    @abstractmethod
    def get_distinct_data_from_column(self, returned_column: Column) -> DataRecord:
        """
        Gets distinct data from a specified data.
        :param returned_column: Column object specifying the data to return data from.
        :return: DataRecord object with the requested distinct data.
        """
        pass

    @abstractmethod
    def get_data_of_column_selection(self, columns: List[Column], filter_elements: List,
                                     filter_column: Column, use_filter: bool = True) -> Optional[DataRecord]:
        """
        Gets data with specified columns filtered by chosen elements in a specified data.
        :param columns: List of Column objects specifying the columns to return.
        :param filter_elements: List of UUIDs specifying the elements to filter by.
        :param filter_column: Column object specifying the data to filter on.
        :param use_filter: Boolean indicating if the filter should be used.
        :return: DataRecord object with the requested data.
        """
        pass

    @abstractmethod
    def get_trajectory_ids(self) -> Optional[DataRecord]:
        """
        Getter for all UUIDs in the Dataset.
        :return: an optional Datarecord with the ids of all trajectories. None if an error occurred
        """
        pass
