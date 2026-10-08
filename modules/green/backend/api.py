from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.complaints import owned_upload
from app.db import get_db
from app.models import AuditLog, User
from app.schemas import Coordinates, Input
from app.security import ADMIN_ROLES, admin_user, current_user
from modules.green.backend.models import PlantingSite, Tree

router = APIRouter(tags=["Green Nellai"])
TreeStatus = Literal["PLANTED", "HEALTHY", "NEEDS_MAINTENANCE", "DAMAGED", "DEAD", "REPLACED"]


class TreeCreate(Coordinates):
    species: str = Field(min_length=2, max_length=160)
    planting_date: date
    organization: str = Field(default="", max_length=160)
    volunteer_group: str = Field(default="", max_length=160)
    image_id: str | None = None
    site_id: str | None = None
    maintenance_date: date | None = None


class TreeUpdate(Input):
    status: TreeStatus
    maintenance_date: date | None = None


class SiteCreate(Coordinates):
    name: str = Field(min_length=3, max_length=160)
    capacity: int = Field(default=0, ge=0, le=100000)
    ownership_status: Literal["UNVERIFIED", "OFFICIALLY_VERIFIED"] = "UNVERIFIED"
    verification_reference: str | None = Field(default=None, max_length=2000)


def tree_dict(t):
    return {
        "id": t.id,
        "species": t.species,
        "latitude": t.latitude,
        "longitude": t.longitude,
        "planting_date": t.planting_date.isoformat(),
        "organization": t.organization,
        "volunteer_group": t.volunteer_group,
        "status": t.status,
        "maintenance_date": t.maintenance_date.isoformat() if t.maintenance_date else None,
        "site_id": t.site_id,
    }


@router.get("/trees")
def trees(db: Session = Depends(get_db)):
    return [tree_dict(t) for t in db.scalars(select(Tree).order_by(Tree.planting_date.desc()).limit(1000))]


@router.post("/trees", status_code=201)
def plant(data: TreeCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.planting_date > date.today():
        raise HTTPException(422, "Record a tree after it is planted")
    if data.site_id and not db.get(PlantingSite, data.site_id):
        raise HTTPException(422, "Planting site not found")
    if data.image_id:
        owned_upload(db, data.image_id, user)
    tree = Tree(**data.model_dump(), created_by=user.id)
    db.add(tree)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="green.tree.create", resource_id=tree.id))
    db.commit()
    return tree_dict(tree)


@router.put("/trees/{tree_id}")
def update_tree(
    tree_id: str, data: TreeUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    tree = db.get(Tree, tree_id)
    if not tree or (tree.created_by != user.id and user.role not in ADMIN_ROLES):
        raise HTTPException(404, "Tree not found or not managed by you")
    tree.status = data.status
    tree.maintenance_date = data.maintenance_date
    db.add(
        AuditLog(
            actor_id=user.id,
            action="green.tree.inspect",
            resource_id=tree.id,
            details=data.model_dump(mode="json"),
        )
    )
    db.commit()
    return tree_dict(tree)


@router.get("/planting-sites")
def sites(db: Session = Depends(get_db)):
    return [
        {
            "id": s.id,
            "name": s.name,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "capacity": s.capacity,
            "ownership_status": s.ownership_status,
        }
        for s in db.scalars(select(PlantingSite).limit(1000))
    ]


@router.post("/planting-sites", status_code=201)
def create_site(data: SiteCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    if data.ownership_status == "OFFICIALLY_VERIFIED" and (
        not data.verification_reference or len(data.verification_reference) < 10
    ):
        raise HTTPException(422, "Official record reference is required; imagery cannot establish ownership")
    site = PlantingSite(
        **data.model_dump(), verified_by=user.id if data.ownership_status == "OFFICIALLY_VERIFIED" else None
    )
    db.add(site)
    db.flush()
    db.add(
        AuditLog(
            actor_id=user.id,
            action="green.site.create",
            resource_id=site.id,
            details={"ownership_status": site.ownership_status},
        )
    )
    db.commit()
    return {"id": site.id}
