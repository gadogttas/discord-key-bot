"""
Miscellaneous SQLAlchemy helpers.
"""

from typing import Any, List, Optional, Union

from sqlalchemy import Index, text, Column, Engine, ClauseElement
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.orm import Session
from sqlalchemy.schema import MetaData, Table
from sqlalchemy.sql.ddl import CreateColumn
from sqlalchemy.types import TypeEngine


def table_exists(name: str, session: Session) -> bool:
    """
    Use SQLAlchemy reflect to check table existences.

    :param string name: Table name to check
    :param Session session: Session to use
    :return: True if table exists, False otherwise
    :rtype: bool
    """
    try:
        table_schema(name, session)
    except NoSuchTableError:
        return False
    return True


def index_exists(table_name: str, index_name: str, session: Session) -> bool:
    """
    Use SQLAlchemy reflect to check index existences.

    :param string table_name: Table name to check
    :param string index_name: Index name to check
    :param Session session: Session to use
    :return: True if table exists, False otherwise
    :rtype: bool
    """
    try:
        return bool(table_index(table_name, index_name, session))
    except NoSuchTableError:
        return False


def table_schema(name: str, session: Session) -> Table:
    """
    :returns: Table schema using SQLAlchemy reflect as it currently exists in the db
    :rtype: Table
    """
    return Table(name, MetaData(), autoload_with=session.bind)


def table_columns(table: Union[str, Table], session: Session) -> List[str]:
    """
    :param string table: Name of table or table schema
    :param Session session: SQLAlchemy Session
    :returns: List of column names in the table or empty list
    """

    if isinstance(table, str):
        table = table_schema(table, session)

    res = []
    for column in table.columns:
        res.append(column.name)

    return res


def table_index(table_name: str, index_name: str, session: Session) -> Index:
    """Finds an index by table name and index name

    :param string table_name: Name of table
    :param string index_name: Name of the index
    :param Session session: SQLAlchemy Session
    :returns: The requested index
    """

    table = table_schema(table_name, session)
    return get_index_by_name(table, index_name)


def drop_index(table_name: str, index_name: str, session: Session) -> None:
    """Drops an index by table name and index name

    :param string table_name: Name of table
    :param string index_name: Name of the index
    :param Session session: SQLAlchemy Session
    """

    index = table_index(table_name, index_name, session)
    index.drop(bind=session.bind)


def table_add_column(
    table: Union[Table, str],
    name: str,
    col_type: Union[TypeEngine, type],
    session: Session,
    default: Any = None,
) -> None:
    """Adds a column to a table

    :param string table: Table to add column to (can be name or schema)
    :param string name: Name of new column to add
    :param col_type: The sqlalchemy column type to add
    :param Session session: SQLAlchemy Session to do the alteration
    :param default: Default value for the created column (optional)
    """
    if isinstance(table, str):
        table = table_schema(table, session)

    if name in table_columns(table, session):
        # If the column already exists, we don't have to do anything.
        return

    # Add the column to the table
    if not isinstance(col_type, TypeEngine):
        # If we got a type class instead of an instance of one, instantiate it
        col_type = col_type()

    column = Column(name=name, type_=col_type, default=default)

    # Use SQLAlchemy's reflection API to get the column DDL
    engine: Engine = session.get_bind()
    meta: MetaData = MetaData()
    meta.reflect(bind=engine)
    col_statement: ClauseElement = CreateColumn(column).compile(bind=engine).statement

    # Add the column
    statement = f'ALTER TABLE {table.name} ADD {col_statement}'
    session.execute(text(statement))

    # Get the new schema with added column
    table = table_schema(table.name, session)
    column = get_column_by_name(table, name)

    # Backfill the desired default value for engines that don't support defaults
    if default is not None and not column.default:
        statement = table.update().values({name: default})
        session.execute(statement)


def drop_tables(names: List[str], session: Session) -> None:
    """Takes a list of table names and drops them from the database if they exist."""
    metadata = MetaData()
    metadata.reflect(bind=session.bind)
    for table in metadata.sorted_tables:
        if table.name in names:
            table.drop(bind=session.bind)


def get_index_by_name(table: Table, name: str) -> Optional[Index]:
    """
    Find declaratively defined index from table by name

    :param table: Table object
    :param string name: Name of the index to get
    :return: Index object
    """
    for index in table.indexes:
        if index.name == name:
            return index


def create_index(table_name: str, session: Session, *column_names: str) -> None:
    """
    Creates an index on specified `columns` in `table_name`

    :param table_name: Name of table to create the index on.
    :param session: Session object which should be used
    :param column_names: The names of the columns that should belong to this index.
    """
    index_name = '_'.join(['ix', table_name, *list(column_names)])
    table = table_schema(table_name, session)
    columns = [getattr(table.c, column) for column in column_names]

    Index(index_name, *columns).create(bind=session.bind)


def get_column_by_name(table: Table, name: str) -> Optional[Column]:
    """
    Find declaratively defined column from table by name

    :param table: The table
    :param name: The name of the column
    :return: Column object
    """
    try:
        return next(column for column in table.columns if column.name == name)
    except StopIteration:
        return None
