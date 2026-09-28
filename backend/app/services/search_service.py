"""Global search: case-insensitive substring matching over each company's own
data, no external index. `.ilike()` compiles to a LOWER()-based comparison on
backends without native ILIKE (SQLite), so this behaves the same on SQLite and
Postgres. This is plain lexical matching -- BUILD-102 (semantic search) would
need embeddings, which needs an LLM/embeddings provider decision that hasn't
been made (see the Day 14 daily log)."""

import uuid

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.material import Material
from app.models.procurement import PurchaseOrder
from app.models.project import Project
from app.models.supplier import Supplier
from app.models.task import Task
from app.models.workforce import Employee
from app.schemas.search import SearchResultItem, SearchResults

MIN_QUERY_LENGTH = 2
PER_TYPE_LIMIT = 8


def _empty(query: str) -> SearchResults:
    return SearchResults(
        query=query, total=0, projects=[], tasks=[], materials=[], suppliers=[],
        purchase_orders=[], documents=[], employees=[],
    )


def search(db: Session, company_id: uuid.UUID, query: str) -> SearchResults:
    query = query.strip()
    if len(query) < MIN_QUERY_LENGTH:
        return _empty(query)

    pattern = f"%{query}%"

    projects = (
        db.query(Project)
        .filter(Project.company_id == company_id)
        .filter((Project.name.ilike(pattern)) | (Project.code.ilike(pattern)) | (Project.client_name.ilike(pattern)))
        .limit(PER_TYPE_LIMIT)
        .all()
    )
    project_results = [
        SearchResultItem(id=p.id, title=p.name, subtitle=p.code, link=f"/projects/{p.id}")
        for p in projects
    ]

    tasks = (
        db.query(Task)
        .filter(Task.company_id == company_id, Task.title.ilike(pattern))
        .limit(PER_TYPE_LIMIT)
        .all()
    )
    task_results = [
        SearchResultItem(id=t.id, title=t.title, subtitle=t.status.value, link=f"/projects/{t.project_id}")
        for t in tasks
    ]

    materials = (
        db.query(Material)
        .filter(Material.company_id == company_id)
        .filter((Material.name.ilike(pattern)) | (Material.sku.ilike(pattern)))
        .limit(PER_TYPE_LIMIT)
        .all()
    )
    material_results = [
        SearchResultItem(id=m.id, title=m.name, subtitle=m.sku, link="/inventory")
        for m in materials
    ]

    suppliers = (
        db.query(Supplier)
        .filter(Supplier.company_id == company_id, Supplier.name.ilike(pattern))
        .limit(PER_TYPE_LIMIT)
        .all()
    )
    supplier_results = [
        SearchResultItem(id=s.id, title=s.name, subtitle=s.email, link="/suppliers")
        for s in suppliers
    ]

    pos = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.company_id == company_id, PurchaseOrder.po_number.ilike(pattern))
        .limit(PER_TYPE_LIMIT)
        .all()
    )
    po_results = [
        SearchResultItem(id=po.id, title=po.po_number, subtitle=po.status.value, link="/procurement")
        for po in pos
    ]

    documents = (
        db.query(Document)
        .filter(Document.company_id == company_id)
        .filter((Document.title.ilike(pattern)) | (Document.original_filename.ilike(pattern)))
        .limit(PER_TYPE_LIMIT)
        .all()
    )
    document_results = [
        SearchResultItem(id=d.id, title=d.title, subtitle=d.category.value, link="/documents")
        for d in documents
    ]

    employees = (
        db.query(Employee)
        .filter(Employee.company_id == company_id)
        .filter((Employee.full_name.ilike(pattern)) | (Employee.designation.ilike(pattern)))
        .limit(PER_TYPE_LIMIT)
        .all()
    )
    employee_results = [
        SearchResultItem(id=e.id, title=e.full_name, subtitle=e.designation, link="/workforce")
        for e in employees
    ]

    total = (
        len(project_results) + len(task_results) + len(material_results) + len(supplier_results)
        + len(po_results) + len(document_results) + len(employee_results)
    )

    return SearchResults(
        query=query,
        total=total,
        projects=project_results,
        tasks=task_results,
        materials=material_results,
        suppliers=supplier_results,
        purchase_orders=po_results,
        documents=document_results,
        employees=employee_results,
    )
