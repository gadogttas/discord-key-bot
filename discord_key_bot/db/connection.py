from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .models import Base, upgrade_tables


def new(uri: str, connection_timeout: str = 15, echo: bool = False) -> sessionmaker:
    engine: Engine = create_engine(
        uri,
        echo=echo,
        connect_args={"timeout": connection_timeout},
    )
    Base.metadata.create_all(engine)

    db_sessionmaker = sessionmaker(bind=engine)
    upgrade_tables(db_sessionmaker)

    return db_sessionmaker
