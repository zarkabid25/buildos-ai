from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import SearchResults
from app.services import search_service

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResults)
def global_search(
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResults:
    return search_service.search(db, current_user.company_id, q)
