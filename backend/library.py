from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(
        String,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class Document(Base):

    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id"
        ),
        nullable=True,
        index=True
    )

    filename = Column(
        String,
        nullable=False
    )

    title = Column(
        String,
        nullable=False
    )

    department = Column(
        String,
        default="Unknown"
    )

    document_type = Column(
        String,
        default="Government Document"
    )

    year = Column(
        String,
        default="Unknown"
    )

    total_pages = Column(
        Integer,
        default=0
    )

    extracted_text = Column(
        Text,
        nullable=False
    )
