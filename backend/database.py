from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = "sqlite:///./tn_insight.db"


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
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

    with engine.begin() as connection:

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_documents_user_id "
                "ON documents (user_id)"
            )
        )
