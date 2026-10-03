"""BUILD-123: request schemas must not accept strings longer than their database
column. SQLite (used by the test suite) ignores VARCHAR(n), but Postgres rejects an
over-long value with an error, so a missing max_length is a 500 in production that
no HTTP test here would catch. This checks the declarations directly instead."""

import importlib
import pkgutil
from inspect import isclass

from pydantic import BaseModel
from sqlalchemy import String

import app.schemas as schemas_pkg
from app import models  # noqa: F401  (registers every mapper)
from app.db.base_class import Base

REQUEST_SUFFIXES = ("Create", "Update", "Base", "Input", "Request")


def _column_lengths() -> dict[str, dict[str, int]]:
    out = {}
    for mapper in Base.registry.mappers:
        out[mapper.class_.__name__] = {
            col.key: col.type.length
            for col in mapper.columns
            if isinstance(col.type, String) and col.type.length
        }
    return out


def _is_plain_str(annotation) -> bool:
    if annotation is str:
        return True
    args = getattr(annotation, "__args__", None)
    return bool(args) and set(args) <= {str, type(None)}


def test_request_strings_fit_their_columns():
    columns = _column_lengths()
    problems = []
    for info in pkgutil.iter_modules(schemas_pkg.__path__):
        module = importlib.import_module(f"app.schemas.{info.name}")
        for name, cls in vars(module).items():
            if not (isclass(cls) and issubclass(cls, BaseModel)) or cls.__module__ != module.__name__:
                continue
            if not name.endswith(REQUEST_SUFFIXES):
                continue
            model_name = name
            for suffix in REQUEST_SUFFIXES:
                model_name = model_name.removesuffix(suffix)
            lengths = columns.get(model_name, {})
            for field_name, field in cls.model_fields.items():
                if field_name not in lengths or not _is_plain_str(field.annotation):
                    continue
                if any(getattr(m, "pattern", None) for m in field.metadata):
                    continue  # a pattern already bounds the length
                max_length = next((m.max_length for m in field.metadata if getattr(m, "max_length", None)), None)
                if max_length is None or max_length > lengths[field_name]:
                    problems.append(f"{name}.{field_name}: max_length={max_length}, column={lengths[field_name]}")
    assert problems == []


def test_overlong_value_is_a_422_not_a_500(client, auth_a):
    res = client.post("/api/v1/projects", headers=auth_a, json={
        "name": "Tower", "code": "TWR", "budget": "1", "client_name": "x" * 256,
    })
    assert res.status_code == 422


def test_null_for_a_required_field_is_a_422_not_a_500(client, auth_a):
    project = client.post("/api/v1/projects", headers=auth_a, json={
        "name": "Tower", "code": "TWR", "budget": "1", "client_name": "Acme",
    }).json()
    res = client.patch(f"/api/v1/projects/{project['id']}", headers=auth_a, json={"name": None})
    assert res.status_code == 422
    assert "name" in res.json()["detail"]
    # A column that may be empty can still be cleared.
    res = client.patch(f"/api/v1/projects/{project['id']}", headers=auth_a, json={"client_name": None})
    assert res.status_code == 200 and res.json()["client_name"] is None
    assert client.get(f"/api/v1/projects/{project['id']}", headers=auth_a).json()["name"] == "Tower"


def test_null_on_other_updates(client, auth_a):
    wh = client.post("/api/v1/warehouses", headers=auth_a, json={"name": "Main"}).json()
    assert client.patch(f"/api/v1/warehouses/{wh['id']}", headers=auth_a, json={"name": None}).status_code == 422
    sup = client.post("/api/v1/suppliers", headers=auth_a, json={"name": "Acme"}).json()
    assert client.patch(f"/api/v1/suppliers/{sup['id']}", headers=auth_a, json={"name": None}).status_code == 422
