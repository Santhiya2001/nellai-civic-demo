import hashlib
from datetime import timedelta
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, now, uid
from app.models import Calendar, Complaint, ComplaintEmail, ComplaintEvent, Upload, User
from app.schemas import Assign, Classification, ComplaintCreate, Merge, Resolve, StatusChange, Verify
from app.security import ADMIN_ROLES, admin_user, current_user
from app.services import (
    apply_assignment,
    auto_assign,
    get_complaint,
    iso,
    nearby,
    record,
    scoped_query,
    serialize,
    working_deadline,
)

router = APIRouter(tags=["Complaints"])
Image.MAX_IMAGE_PIXELS = 16_000_000


def owned_upload(db, image_id, user):
    upload = db.get(Upload, image_id)
    if not upload or upload.owner_id != user.id or not Path(settings().upload_dir, upload.filename).is_file():
        raise HTTPException(422, "Upload a photograph from your own account first")
    return upload


@router.post("/uploads", status_code=201)
def upload_image(file: UploadFile, user: User = Depends(current_user), db: Session = Depends(get_db)):
    raw = file.file.read(settings().max_upload_mb * 1024 * 1024 + 1)
    if len(raw) > settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Image exceeds the upload limit")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Use a JPEG, PNG or WebP photograph")
    try:
        with Image.open(BytesIO(raw)) as original:
            if (
                original.format not in {"JPEG", "PNG", "WEBP"}
                or original.width * original.height > Image.MAX_IMAGE_PIXELS
            ):
                raise HTTPException(415, "Unsupported image or image dimensions too large")
            original.load()
            from PIL import ImageOps

            clean = ImageOps.exif_transpose(original).convert("RGB")
            clean.thumbnail((2000, 2000))
            output = BytesIO()
            clean.save(output, format="JPEG", quality=88)
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise HTTPException(415, "The file is not a valid supported photograph") from exc
    content = output.getvalue()
    image_id = uid()
    folder = Path(settings().upload_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{image_id}.jpg"
    path.write_bytes(content)
    path.chmod(0o600)
    db.add(
        Upload(id=image_id, owner_id=user.id, filename=path.name, sha256=hashlib.sha256(content).hexdigest())
    )
    db.commit()
    return {"id": image_id, "url": f"/api/v1/uploads/{image_id}"}


@router.get("/uploads/{image_id}")
def read_image(image_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    upload = db.get(Upload, image_id)
    if not upload:
        raise HTTPException(404, "Image not found")
    allowed = upload.owner_id == user.id or user.role in ADMIN_ROLES
    if not allowed:
        query = scoped_query(user).where(
            or_(Complaint.image_id == image_id, Complaint.resolution_image_id == image_id)
        )
        allowed = db.scalar(query) is not None
    path = Path(settings().upload_dir, upload.filename)
    if not allowed or not path.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/complaints", status_code=201)
def create_complaint(
    data: ComplaintCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_upload(db, data.image_id, user)
    complaint = Complaint(
        **data.model_dump(),
        user_id=user.id,
        reference="NGC-" + uid()[:8].upper(),
        status="REPORTED",
        escalation_level=0,
        cycle=0,
    )
    db.add(complaint)
    db.flush()
    record(db, complaint, user.id, "Issue reported with location and photographic evidence.")
    auto_assign(db, complaint)
    if recipient := settings().complaint_alert_email:
        db.add(ComplaintEmail(complaint_id=complaint.id, recipient=str(recipient)))
    db.commit()
    return serialize(complaint, db)


@router.get("/complaints")
def list_complaints(
    status: str | None = None,
    category: str | None = None,
    q: str = Query(default="", max_length=120),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = scoped_query(user)
    if status:
        query = query.where(Complaint.status == status)
    if category:
        query = query.where(Complaint.category == category)
    if q:
        query = query.where(
            or_(
                Complaint.title.icontains(q, autoescape=True),
                Complaint.reference.icontains(q, autoescape=True),
            )
        )
    return [
        serialize(c, db)
        for c in db.scalars(query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit))
    ]


@router.get("/complaints/nearby")
def nearby_complaints(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius: float = Query(default=1000, gt=0, le=10000),
    db: Session = Depends(get_db),
):
    return [serialize(c, db, public=True) for c in nearby(db, latitude, longitude, radius)]


@router.get("/complaints/{complaint_id}")
def detail(complaint_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    complaint = get_complaint(db, complaint_id, user)
    events = db.scalars(
        select(ComplaintEvent)
        .where(ComplaintEvent.complaint_id == complaint_id)
        .order_by(ComplaintEvent.created_at)
    )
    return serialize(complaint, db) | {
        "history": [
            {"status": e.status, "message": e.message, "created_at": iso(e.created_at)} for e in events
        ]
    }


@router.post("/complaints/{complaint_id}/assign")
def assign(complaint_id: str, data: Assign, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    complaint = get_complaint(db, complaint_id, user, manage=True)
    if complaint.status in {"CLOSED", "REJECTED", "RESOLVED", "VERIFICATION"}:
        raise HTTPException(409, "This complaint cannot be assigned in its current state")
    calendar = db.get(Calendar, data.calendar_id)
    if not calendar:
        raise HTTPException(422, "Calendar not found")
    apply_assignment(
        db,
        complaint,
        data.authority_id,
        calendar,
        data.deadline_days,
        complaint.escalation_steps or [],
        user.id,
        data.reason,
    )
    db.commit()
    return serialize(complaint, db)


@router.post("/complaints/{complaint_id}/status")
def status_change(
    complaint_id: str, data: StatusChange, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    complaint = get_complaint(db, complaint_id, user, manage=True)
    transitions = {
        "ASSIGNED": {"ACKNOWLEDGED"},
        "ACKNOWLEDGED": {"IN_PROGRESS"},
        "REPORTED": {"REJECTED"},
        "AI_ANALYZED": {"REJECTED"},
    }
    if data.status == "REJECTED" and user.role not in ADMIN_ROLES:
        raise HTTPException(403, "Only administrators can reject reports")
    if data.status not in transitions.get(complaint.status, set()):
        raise HTTPException(409, f"Cannot move from {complaint.status} to {data.status}")
    complaint.status = data.status
    record(db, complaint, user.id, data.reason)
    db.commit()
    return serialize(complaint, db)


@router.post("/complaints/{complaint_id}/classify")
def classify(
    complaint_id: str, data: Classification, user: User = Depends(admin_user), db: Session = Depends(get_db)
):
    complaint = get_complaint(db, complaint_id, user, manage=True)
    if complaint.status in {"CLOSED", "REJECTED"}:
        raise HTTPException(409, "Closed reports cannot be reclassified")
    complaint.category = data.category
    complaint.severity = data.severity
    record(db, complaint, user.id, f"Human classification: {data.category}, {data.severity}. {data.reason}")
    db.commit()
    return serialize(complaint, db)


@router.post("/complaints/{complaint_id}/resolve")
def resolve(
    complaint_id: str, data: Resolve, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    complaint = get_complaint(db, complaint_id, user, manage=True)
    if complaint.status != "IN_PROGRESS":
        raise HTTPException(409, "Only an issue in progress can be resolved")
    owned_upload(db, data.image_id, user)
    complaint.resolution_description = data.description
    complaint.resolution_image_id = data.image_id
    complaint.resolution_latitude = data.latitude
    complaint.resolution_longitude = data.longitude
    complaint.resolved_by = user.id
    complaint.resolved_at = now()
    complaint.status = "RESOLVED"
    record(db, complaint, user.id, "Resolution submitted with photograph and location.")
    complaint.status = "VERIFICATION"
    record(db, complaint, user.id, "Awaiting citizen verification.")
    db.commit()
    return serialize(complaint, db)


@router.post("/complaints/{complaint_id}/verify")
def verify(
    complaint_id: str, data: Verify, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    complaint = get_complaint(db, complaint_id, user)
    if complaint.user_id != user.id:
        raise HTTPException(403, "Only the reporting citizen can verify the resolution")
    if complaint.status != "VERIFICATION" or complaint.merged_into:
        raise HTTPException(409, "This complaint is not awaiting verification")
    complaint.status = "CLOSED" if data.resolved else "IN_PROGRESS"
    if not data.resolved:
        calendar = db.get(Calendar, complaint.calendar_id)
        complaint.deadline = working_deadline(now(), 1, calendar)
        complaint.next_escalation_at = complaint.deadline
        complaint.escalation_level = 0
        complaint.cycle += 1
    record(
        db,
        complaint,
        user.id,
        ("Citizen confirmed resolution. " if data.resolved else "Citizen reopened the issue. ") + data.reason,
    )
    db.commit()
    return serialize(complaint, db)


@router.get("/complaints/{complaint_id}/duplicates")
def duplicates(complaint_id: str, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    complaint = get_complaint(db, complaint_id, user)
    candidates = nearby(
        db,
        complaint.latitude,
        complaint.longitude,
        100,
        complaint.category,
        complaint.created_at - timedelta(days=7),
    )
    return [
        {
            "complaint": serialize(c, db),
            "text_similarity": round(
                SequenceMatcher(None, complaint.description.lower(), c.description.lower()).ratio(), 3
            ),
            "reason": "Same category within 100 m and 7 days; human review required",
        }
        for c in candidates
        if c.id != complaint.id and abs((c.created_at - complaint.created_at).total_seconds()) <= 7 * 86400
    ]


@router.post("/complaints/{complaint_id}/merge")
def merge(complaint_id: str, data: Merge, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    source = get_complaint(db, complaint_id, user, manage=True)
    target = get_complaint(db, data.target_id, user)
    if source.id == target.id or target.merged_into or source.status in {"CLOSED", "REJECTED"}:
        raise HTTPException(409, "Choose a different, unmerged target and an open source")
    if db.scalar(select(Complaint).where(Complaint.merged_into == source.id)):
        raise HTTPException(409, "A report with linked duplicates cannot itself be merged")
    source.merged_into = target.id
    source.next_escalation_at = None
    record(db, source, user.id, f"Linked as a duplicate of {target.reference}. {data.reason}")
    db.commit()
    return serialize(source, db)
