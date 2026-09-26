import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.ai import AiProposal
from app.models.enums import AiProposalStatus, AiProposalType
from app.models.user import User
from app.schemas.procurement import MaterialRequestCreate, MaterialRequestItemInput
from app.services import procurement_service
from app.services.material_service import get_material
from app.services.project_service import get_project

MAX_PROPOSAL_ITEMS = 30


def create_material_request_proposal(
    db: Session,
    company_id: uuid.UUID,
    user: User,
    conversation_id: uuid.UUID | None,
    project_id: uuid.UUID,
    items: list[dict],
    notes: str | None,
) -> AiProposal:
    """Stores a *draft*. Nothing in the real material_requests table changes here."""
    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A proposal needs at least one item")
    if len(items) > MAX_PROPOSAL_ITEMS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"At most {MAX_PROPOSAL_ITEMS} items per proposal")

    project = get_project(db, company_id, project_id)

    payload_items = []
    parts = []
    for raw in items:
        try:
            material_id = uuid.UUID(str(raw["material_id"]))
            quantity = Decimal(str(raw["quantity"]))
        except (KeyError, ValueError, InvalidOperation):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Each item needs a valid material_id and quantity")
        if quantity <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quantities must be greater than zero")

        material = get_material(db, company_id, material_id)  # 404s for another company's material
        payload_items.append(
            {"material_id": str(material.id), "material_name": material.name, "unit": material.unit, "quantity": str(quantity)}
        )
        parts.append(f"{quantity:g} {material.unit} {material.name}")

    proposal = AiProposal(
        company_id=company_id,
        conversation_id=conversation_id,
        proposal_type=AiProposalType.MATERIAL_REQUEST,
        summary=f"Request {', '.join(parts)} for {project.name}"[:500],
        payload={"project_id": str(project.id), "notes": notes, "items": payload_items},
        created_by_id=user.id,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def list_proposals(
    db: Session, company_id: uuid.UUID, proposal_status: AiProposalStatus | None = None
) -> list[AiProposal]:
    query = db.query(AiProposal).filter(AiProposal.company_id == company_id)
    if proposal_status:
        query = query.filter(AiProposal.status == proposal_status)
    return query.order_by(AiProposal.created_at.desc()).all()


def get_proposal(db: Session, company_id: uuid.UUID, proposal_id: uuid.UUID) -> AiProposal:
    proposal = (
        db.query(AiProposal)
        .filter(AiProposal.company_id == company_id, AiProposal.id == proposal_id)
        .first()
    )
    if not proposal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposal not found")
    return proposal


def _require_pending(proposal: AiProposal) -> None:
    if proposal.status != AiProposalStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Proposal was already {proposal.status.value}")


def approve_proposal(db: Session, company_id: uuid.UUID, user: User, proposal_id: uuid.UUID) -> AiProposal:
    proposal = get_proposal(db, company_id, proposal_id)
    _require_pending(proposal)

    # Mark it approved in the same transaction that creates the real record
    # (create_material_request commits the session), so a proposal can't be
    # approved twice or end up "pending" with its request already created.
    proposal.status = AiProposalStatus.APPROVED
    proposal.decided_by_id = user.id
    proposal.decided_at = datetime.now(timezone.utc)

    payload = proposal.payload
    try:
        request = procurement_service.create_material_request(
            db,
            company_id,
            user.id,  # the approving person owns the request, not the assistant
            MaterialRequestCreate(
                project_id=uuid.UUID(payload["project_id"]),
                notes=payload.get("notes"),
                items=[
                    MaterialRequestItemInput(material_id=uuid.UUID(i["material_id"]), quantity=Decimal(i["quantity"]))
                    for i in payload["items"]
                ],
            ),
        )
    except Exception:
        db.rollback()  # discard the approved-status change; the proposal stays pending
        raise

    proposal.result_ref = request.id
    db.commit()
    db.refresh(proposal)
    return proposal


def reject_proposal(db: Session, company_id: uuid.UUID, user: User, proposal_id: uuid.UUID) -> AiProposal:
    proposal = get_proposal(db, company_id, proposal_id)
    _require_pending(proposal)
    proposal.status = AiProposalStatus.REJECTED
    proposal.decided_by_id = user.id
    proposal.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(proposal)
    return proposal
