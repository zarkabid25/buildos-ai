import uuid

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    id: uuid.UUID
    title: str
    subtitle: str | None = None
    link: str


class SearchResults(BaseModel):
    query: str
    total: int
    projects: list[SearchResultItem]
    tasks: list[SearchResultItem]
    materials: list[SearchResultItem]
    suppliers: list[SearchResultItem]
    purchase_orders: list[SearchResultItem]
    documents: list[SearchResultItem]
    employees: list[SearchResultItem]
