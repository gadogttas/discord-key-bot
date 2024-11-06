from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .models import Base, upgrade_tables


def new(uri: str, connection_timeout: str = 15) -> sessionmaker:
    engine: Engine = create_engine(
        uri,
        echo=False,
        connect_args={"timeout": connection_timeout},
    )
    Base.metadata.create_all(engine)

    db_session_maker = sessionmaker(bind=engine)
    upgrade_tables(db_session_maker)

    return db_session_maker
