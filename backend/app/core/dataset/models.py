import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class DatasetVersion(Base):
    __tablename__ = "dataset_version"

    id: Mapped[str] = mapped_column(String, primary_key=True)

