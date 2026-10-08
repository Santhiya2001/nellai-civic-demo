from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, now
from app.models import AuditLog, Complaint, LoginSession, Notification, Upload, User
from app.schemas import DeleteAccount, Login, Refresh, Register
from app.security import (
    DUMMY_HASH,
    access_token,
    current_user,
    decode_token,
    digest,
    encode_token,
    hasher,
    new_session,
    password_ok,
    user_public,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def cookie(response, token):
    response.set_cookie(
        "nellai_refresh",
        token,
        httponly=True,
        secure=settings().environment == "production",
        samesite="strict",
        max_age=settings().refresh_days * 86400,
        path="/api/v1/auth",
    )
    response.headers["Cache-Control"] = "no-store"


def token_response(response, session, refresh):
    cookie(response, refresh)
    return {
        "access_token": access_token(session),
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings().access_minutes * 60,
    }


@router.post("/register", status_code=201)
def register(data: Register, db: Session = Depends(get_db)):
    filters = []
    if data.email:
        filters.append(User.email == str(data.email))
    if data.phone:
        filters.append(User.phone == data.phone)
    if db.scalar(select(User).where(or_(*filters))):
        raise HTTPException(409, "This contact is already registered")
    user = User(
        name=data.name,
        email=str(data.email) if data.email else None,
        phone=data.phone,
        password_hash=hasher.hash(data.password),
        role="CITIZEN",
    )
    db.add(user)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="account.register", resource_id=user.id))
    db.commit()
    return user_public(user)


@router.post("/login")
def login(data: Login, response: Response, db: Session = Depends(get_db)):
    identifier = data.identifier.lower()
    user = db.scalar(select(User).where(or_(User.email == identifier, User.phone == identifier)))
    valid = password_ok(user.password_hash if user else DUMMY_HASH, data.password)
    if not user or not valid or not user.active:
        raise HTTPException(401, "Incorrect credentials")
    session, refresh = new_session(db, user)
    db.add(AuditLog(actor_id=user.id, action="account.login", resource_id=user.id))
    db.commit()
    return token_response(response, session, refresh) | {"user": user_public(user)}


def refresh_source(data, request):
    if data and data.refresh_token:
        return data.refresh_token
    # Cookies require an explicit trusted Origin. Mobile clients use a body token.
    if request.headers.get("origin") not in settings().origins:
        raise HTTPException(403, "Untrusted request origin")
    token = request.cookies.get("nellai_refresh")
    if not token:
        raise HTTPException(401, "Refresh token required")
    return token


@router.post("/refresh")
def refresh(response: Response, request: Request, data: Refresh | None = None, db: Session = Depends(get_db)):
    token = refresh_source(data, request)
    claims = decode_token(token, "refresh")
    session = db.get(LoginSession, claims["sid"])
    user = db.get(User, claims["sub"])
    if (
        not session
        or session.revoked
        or session.expires_at < now()
        or not user
        or not user.active
        or session.user_id != user.id
    ):
        raise HTTPException(401, "Refresh session expired")
    replacement = encode_token(user.id, session.id, "refresh", session.expires_at)
    changed = db.execute(
        update(LoginSession)
        .where(
            LoginSession.id == session.id,
            LoginSession.refresh_hash == digest(token),
            LoginSession.revoked.is_(False),
        )
        .values(refresh_hash=digest(replacement))
    )
    if changed.rowcount != 1:
        session.revoked = True
        db.commit()
        raise HTTPException(401, "Refresh token reuse detected; sign in again")
    db.commit()
    return token_response(response, session, replacement)


@router.post("/logout", status_code=204)
def logout(response: Response, request: Request, data: Refresh | None = None, db: Session = Depends(get_db)):
    token = refresh_source(data, request)
    claims = decode_token(token, "refresh")
    session = db.get(LoginSession, claims["sid"])
    if session:
        session.revoked = True
        db.commit()
    response.delete_cookie("nellai_refresh", path="/api/v1/auth")


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_public(user)


@router.delete("/me", status_code=204)
def delete_me(data: DeleteAccount, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not password_ok(user.password_hash, data.password):
        raise HTTPException(401, "Password confirmation failed")
    if user.role in {"ADMIN", "SUPER_ADMIN", "AUTHORITY"}:
        raise HTTPException(409, "Transfer staff responsibilities before account deletion")
    from pathlib import Path

    from app.modules import installed_manifests

    user.active = False
    user.email = None
    user.phone = None
    user.name = "Deleted account"
    user.password_hash = hasher.hash(__import__("secrets").token_urlsafe(48))
    for session in db.scalars(select(LoginSession).where(LoginSession.user_id == user.id)):
        session.revoked = True
    for complaint in db.scalars(select(Complaint).where(Complaint.user_id == user.id)):
        complaint.user_id = None
        complaint.title = "Civic issue (reporter deleted)"
        complaint.description = "Reporter content removed on account deletion."
        complaint.locality = ""
        complaint.image_id = None
    for upload in db.scalars(select(Upload).where(Upload.owner_id == user.id)):
        Path(settings().upload_dir, upload.filename).unlink(missing_ok=True)
    for notification in db.scalars(select(Notification).where(Notification.user_id == user.id)):
        db.delete(notification)
    if "volunteer" in installed_manifests():
        from modules.volunteer.backend.models import Volunteer

        profile = db.get(Volunteer, user.id)
        if profile:
            db.delete(profile)
    db.add(AuditLog(actor_id=user.id, action="account.delete", resource_id=user.id))
    db.commit()
