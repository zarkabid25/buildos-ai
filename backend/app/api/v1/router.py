from fastapi import APIRouter

from app.api.v1 import (
    auth,
    boq,
    companies,
    forecast,
    health,
    inventory,
    materials,
    milestones,
    project_members,
    projects,
    tasks,
    warehouses,
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
