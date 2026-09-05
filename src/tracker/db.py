from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url)


def get_sessionmaker(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(database_url))
