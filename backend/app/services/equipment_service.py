import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, EquipmentMaintenance
from app.schemas.equipment import EquipmentCreate, EquipmentMaintenanceCreate, EquipmentUpdate, MaintenanceReminder

# Equipment with a maintenance due date inside this window (including overdue)
# shows up in the reminder list.
REMINDER_WINDOW_DAYS = 14


def list_equipment(db: Session, company_id: uuid.UUID) -> list[Equipment]:
    return (
        db.query(Equipment)
        .filter(Equipment.company_id == company_id)
        .order_by(Equipment.name.asc())
        .all()
    )


def get_equipment(db: Session, company_id: uuid.UUID, equipment_id: uuid.UUID) -> Equipment:
    equipment = (
        db.query(Equipment)
        .filter(Equipment.company_id == company_id, Equipment.id == equipment_id)
        .first()
    )
    if not equipment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Equipment not found")
    return equipment


def create_equipment(db: Session, company_id: uuid.UUID, payload: EquipmentCreate) -> Equipment:
    equipment = Equipment(company_id=company_id, **payload.model_dump())
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def update_equipment(
    db: Session, company_id: uuid.UUID, equipment_id: uuid.UUID, payload: EquipmentUpdate
) -> Equipment:
    equipment = get_equipment(db, company_id, equipment_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(equipment, field, value)
    db.commit()
    db.refresh(equipment)
    return equipment


def add_maintenance_record(
    db: Session, company_id: uuid.UUID, equipment_id: uuid.UUID, payload: EquipmentMaintenanceCreate
) -> EquipmentMaintenance:
    get_equipment(db, company_id, equipment_id)
    record = EquipmentMaintenance(company_id=company_id, equipment_id=equipment_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_maintenance_records(
    db: Session, company_id: uuid.UUID, equipment_id: uuid.UUID
) -> list[EquipmentMaintenance]:
    get_equipment(db, company_id, equipment_id)
    return (
        db.query(EquipmentMaintenance)
        .filter(EquipmentMaintenance.company_id == company_id, EquipmentMaintenance.equipment_id == equipment_id)
        .order_by(EquipmentMaintenance.maintenance_date.desc())
        .all()
    )


def get_maintenance_reminders(db: Session, company_id: uuid.UUID) -> list[MaintenanceReminder]:
    """For each piece of equipment, look at its most recent maintenance record's
    next_due_date and flag it if that date is overdue or within the reminder
    window. Equipment with no maintenance history yet has nothing to remind
    about, so it's simply not included -- not flagged as a false "overdue"."""
    equipment_list = list_equipment(db, company_id)
    today = date.today()
    reminders: list[MaintenanceReminder] = []

    for equipment in equipment_list:
        latest = (
            db.query(EquipmentMaintenance)
            .filter(
                EquipmentMaintenance.company_id == company_id,
                EquipmentMaintenance.equipment_id == equipment.id,
                EquipmentMaintenance.next_due_date.isnot(None),
            )
            .order_by(EquipmentMaintenance.maintenance_date.desc())
            .first()
        )
        if not latest or not latest.next_due_date:
            continue

        days_until_due = (latest.next_due_date - today).days
        if days_until_due <= REMINDER_WINDOW_DAYS:
            reminders.append(
                MaintenanceReminder(
                    equipment_id=equipment.id,
                    equipment_name=equipment.name,
                    next_due_date=latest.next_due_date,
                    days_until_due=days_until_due,
                    is_overdue=days_until_due < 0,
                )
            )

    return sorted(reminders, key=lambda r: r.days_until_due)
