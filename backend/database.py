import os

from sqlalchemy import (
    create_engine,
    inspect,
    text
)

from sqlalchemy.orm import (
    sessionmaker,
    declarative_base
)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./tn_insight.db"
)


if DATABASE_URL.startswith(
    "postgres://"
):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


if DATABASE_URL.startswith(
    "sqlite"
):

    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False
        },
        pool_pre_ping=True
    )

else:

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def ensure_schema():

    inspector = inspect(
        engine
    )

    table_names = (
        inspector.get_table_names()
    )

    if "documents" not in table_names:
        return

    document_columns = {
        column["name"]
        for column
        in inspector.get_columns(
            "documents"
        )
    }

    if "user_id" not in document_columns:

        with engine.begin() as connection:

            connection.execute(
                text(
                    "ALTER TABLE documents "
                    "ADD COLUMN user_id INTEGER"
                )
            )

    inspector = inspect(
        engine
    )

    index_names = {
        index["name"]
        for index
        in inspector.get_indexes(
            "documents"
        )
        if index.get("name")
    }

    if (
        "ix_documents_user_id"
        not in index_names
    ):

        with engine.begin() as connection:

            connection.execute(
                text(
                    "CREATE INDEX "
                    "ix_documents_user_id "
                    "ON documents (user_id)"
                )
            )