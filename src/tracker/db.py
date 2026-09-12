from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def get_engine(database_url: str) -> Engine:
    # Supabase's connection pooler runs PgBouncer in transaction mode, which
    # hands the same server connection to different clients between
    # statements. psycopg3 caches prepared statements under per-connection
    # names ("_pg3_0", ...), so two clients eventually collide and the
    # server rejects the query with
    #   (psycopg.errors.DuplicatePreparedStatement) prepared statement
    #   "_pg3_0" already exists
    # Turning the prepare cache off is the documented workaround, and costs
    # nothing here: every query this project runs is either a one-off or
    # cheap enough that plan reuse is not what makes it fast.
    return create_engine(database_url, connect_args={"prepare_threshold": None})


@lru_cache
def get_sessionmaker(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(database_url))
