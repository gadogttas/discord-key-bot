import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from .models import Base


engine = create_engine(
    os.environ.get("SQLALCHEMY_URI", "sqlite:///:memory:"), echo=False
)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
