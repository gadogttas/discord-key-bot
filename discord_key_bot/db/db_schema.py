from typing import Callable

from sqlalchemy import Column, Integer, String

from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()


class TableVersion(Base):
    __tablename__ = "table_schema"

    id = Column(Integer, primary_key=True)
    entity = Column(String)
    version = Column(Integer)

    def __init__(self, entity: str, version: int = 0):
        self.entity = entity
        self.version = version

    def __str__(self) -> str:
        return f"<TableSchema(entity={self.entity},version={self.version})>"


def get_version(entity: str, session: Session) -> int:
    table_version = session.query(TableVersion).filter(TableVersion.entity == entity).first()
    if not table_version:
        return -1
    else:
        return table_version.version


def set_version(entity: str, version: int, session: Session) -> None:
    table_version = session.query(TableVersion).filter(TableVersion.entity == entity).first()
    if not table_version:
        table_version = TableVersion(entity=entity, version=version)
        session.add(table_version)

    if table_version.version < version:
        table_version.version = version

    session.commit()


def upgrade(entity: str, upgrade_func: Callable, session: Session) -> None:
    with session:
        current_ver = get_version(entity, session=session)
        try:
            new_ver = upgrade_func(current_ver)
            set_version(entity, new_ver, session=session)
        except Exception as e:
            session.rollback()
            raise e

        if new_ver > current_ver:
            set_version(entity, new_ver, session=session)
        elif new_ver < current_ver:
            session.rollback()
            raise ValueError("Cannot downgrade table version")
