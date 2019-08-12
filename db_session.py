# encoding: utf8

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from conf import config


def _create_mysql_engine():
    engine = create_engine(
            'mysql://{}:{}@{}:{}/{}?charset=utf8'.format(
                 config.db.username,
                 config.db.password,
                 config.db.host,
                 config.db.port,
                 config.db.dbname, 
                 )
            )

    return engine

engine = _create_mysql_engine()

Session = sessionmaker(bind=engine)


@contextmanager
def open_session(session_cls, commit=False):
    session = session_cls()
    try:
        yield session
        if commit:
            session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
