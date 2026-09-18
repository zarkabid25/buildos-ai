"""Creates all tables directly from the SQLAlchemy models against a local SQLite
file, for quick local UI testing without Postgres/Docker. NOT how migrations work
in real deployments -- production always goes through Alembic against Postgres
(see backend/alembic/). This script is a dev convenience only."""

from sqlalchemy import create_engine

from app.db.base_class import Base
from app import models  # noqa: F401  (registers all models on Base.metadata)

engine = create_engine("sqlite:///./buildos_dev.db")
Base.metadata.create_all(engine)
print("SQLite dev database created at backend/buildos_dev.db")
