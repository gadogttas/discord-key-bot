import os
from sqlalchemy import create_engine, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from .models import Base


engine: Engine = create_engine(
    os.environ.get("SQLALCHEMY_URI", "sqlite:///:memory:"),
    echo=False,
    connect_args={"timeout": 15},
)
Base.metadata.create_all(engine)
Session: sessionmaker = sessionmaker(bind=engine)
