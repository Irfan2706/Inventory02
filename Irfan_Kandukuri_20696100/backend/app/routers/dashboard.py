from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import require_roles
from app.database import get_db
from app.models import UserRole
from app.schemas import DashboardSummary
from app.services import dashboard_summary


router = APIRouter()


@router.get("", response_model=DashboardSummary)
def get_dashboard(
    db: Session = Depends(get_db),
    _user=Depends(require_roles([UserRole.manager])),
):
    return DashboardSummary(**dashboard_summary(db))
