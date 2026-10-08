import hashlib
import secrets
from datetime import timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, now, uid
from app.models import LoginSession, User

hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))
ADMIN_ROLES = {"ADMIN", "SUPER_ADMIN"}


def password_ok(stored, candidate):
    try:
        return hasher.verify(stored, candidate)
    except VerificationError:
        return False


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def encode_token(user_id, session_id, kind, expires):
    return jwt.encode(
        {
            "sub": user_id,
            "sid": session_id,
            "type": kind,
            "jti": uid(),
            "iat": now().replace(tzinfo=timezone.utc),
            "exp": expires.replace(tzinfo=timezone.utc),
            "iss": "nellai-green-civic",
            "aud": "nellai-api",
        },
        settings().jwt_secret,
        algorithm="HS256",
    )


def decode_token(token, kind):
    try:
        claims = jwt.decode(
            token,
            settings().jwt_secret,
            algorithms=["HS256"],
            issuer="nellai-green-civic",
            audience="nellai-api",
            options={"require": ["sub", "sid", "type", "jti", "iat", "exp"]},
        )
        if claims["type"] != kind:
            raise jwt.InvalidTokenError()
        return claims
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, "Session expired or token invalid") from exc


def new_session(db, user):
    session = LoginSession(
        id=uid(), user_id=user.id, expires_at=now() + timedelta(days=settings().refresh_days), refresh_hash=""
    )
    refresh = encode_token(user.id, session.id, "refresh", session.expires_at)
    session.refresh_hash = digest(refresh)
    db.add(session)
    db.flush()
    return session, refresh


def access_token(session):
    return encode_token(
        session.user_id, session.id, "access", now() + timedelta(minutes=settings().access_minutes)
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
):
    if not credentials:
        raise HTTPException(401, "Sign in to continue")
    claims = decode_token(credentials.credentials, "access")
    session = db.get(LoginSession, claims["sid"])
    user = db.get(User, claims["sub"])
    if (
        not session
        or session.revoked
        or session.expires_at < now()
        or session.user_id != claims["sub"]
        or not user
        or not user.active
    ):
        raise HTTPException(401, "Session no longer active")
    return user


def roles(*allowed):
    def check(user: User = Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(403, "This action is not permitted for your role")
        return user

    return check


admin_user = roles("ADMIN", "SUPER_ADMIN")


def user_public(user):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "authority_id": user.authority_id,
    }
