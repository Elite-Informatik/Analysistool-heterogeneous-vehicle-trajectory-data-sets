from enum import Enum


class SQLQueries(Enum):
    """
    holds all sql queries
    """

    CREATETABLE = "CREATE TABLE {tablename} ({columns})"
    DROPTABLE = "DROP TABLE {tablename};"
    SELECT = "SELECT {columns}"
    FROM = " FROM {tablename} AS t"
    WHERE = " WHERE {filter}"
    SELECT_FROM = "SELECT {columns} FROM {tablename}"
    SELECTFILTERED = "SELECT {columns} FROM {tablename} WHERE {filter}"
    NOT = "NOT({filter})"
    SELECTGROUPEDFILTERED = "SELECT {data} FROM {tablename} WHERE {filter} GROUP BY {data}"
    GROUPED = " GROUP BY {columns}"
    WHEREIN = " WHERE {column} IN ({values})"
    SELECTINFILTERED = "SELECT {columns} FROM {tablename} WHERE {data} IN ({values}) AND {filter}"
    INSERT = "INSERT INTO {tablename} VALUES {values}"
    GET_COLUMNS = "SELECT column_name FROM information_schema.columns WHERE table_name = '{tablename}'"
    GET_TABLES_WITH_SIZE = """
                            SELECT 
                                table_name, 
                                pg_total_relation_size(quote_ident(table_name)) / 1024 / 1024 AS size_in_mb 
                            FROM 
                                information_schema.tables 
                            WHERE 
                                table_schema = 'public'
                            ORDER BY
                                size_in_mb DESC;
                            """
    TABLE_SIZE = """SELECT
                        pg_total_relation_size(quote_ident(table_name)) / 1024 / 1024 AS size_in_mb
                    FROM
                        information_schema.tables
                    WHERE
                        table_name='{tablename}'
                    LIMIT 1
                    """
    UPDATE = """UPDATE {tablename}
                SET {update_columns}
                WHERE {key_column}"""
    DELETE = """DELETE FROM {tablename}
                WHERE {key_column}"""
