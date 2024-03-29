from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .models import Base


def new(uri: str, connection_timeout: str = 15) -> sessionmaker:
    engine: Engine = create_engine(
        uri,
        echo=False,
        connect_args={"timeout": connection_timeout},
    )
    Base.metadata.create_all(engine)

    return sessionmaker(bind=engine)
