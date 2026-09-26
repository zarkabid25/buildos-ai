from fastapi import APIRouter

from app.api.v1 import (
    auth,
    boq,
    companies,
    daily_reports,
    equipment,
    finance,
    forecast,
    health,
    inventory,
    materials,
    milestones,
    procurement,
    project_members,
    projects,
    suppliers,
    tasks,
    warehouses,
    workforce,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(projects.router)
api_router.include_router(project_members.router)
api_router.include_router(milestones.router)
api_router.include_router(tasks.router)
api_router.include_router(boq.router)
api_router.include_router(materials.router)
api_router.include_router(warehouses.router)
api_router.include_router(inventory.router)
api_router.include_router(forecast.router)
api_router.include_router(suppliers.router)
api_router.include_router(procurement.router)
api_router.include_router(finance.router)
api_router.include_router(workforce.router)
api_router.include_router(equipment.router)
api_router.include_router(daily_reports.router)
