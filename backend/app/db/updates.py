from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import inspect

from app.db.base_class import Base


def apply_changes(obj: Base, changes: dict[str, Any]) -> None:
    """Copy a PATCH body's fields onto a model. Update schemas make every field
    optional so it can be omitted, which also lets a client send an explicit null;
    for a NOT NULL column that would be a database error (a 500), so it's a 422 here."""
    columns = inspect(type(obj)).columns
    for field, value in changes.items():
        column = columns.get(field)
        if value is None and column is not None and not column.nullable:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{field} cannot be empty")
        setattr(obj, field, value)
