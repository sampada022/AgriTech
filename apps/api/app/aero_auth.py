"""Accounts for the AeroScout website: email + password, session in an HttpOnly cookie (so <img> tags are authorised too)."""
from __future__ import annotations

import os
import re
import time
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from .aero_models import AeroUser
from .db import engine, get_session
from .models import SessionToken, now
from .security import expired, hash_pin, hash_token, new_salt, new_token
import hmac

COOKIE = "aero_session"
TTL = timedelta(hours=12)
DEMO_EMAIL = os.environ.get("AEROSCOUT_DEMO_EMAIL", "demo@aeroscout.app")
DEMO_PASSWORD = os.environ.get("AEROSCOUT_DEMO_PASSWORD", "aeroscout-demo")
auth_router = APIRouter(prefix="/api/aeroscout/auth", tags=["aeroscout-auth"])
_fails: dict[str, list[float]] = {}  # email -> recent failure times (in-memory, per process)


class Credentials(BaseModel):
    email: str
    password: str


class Registration(Credentials):
    name: str


def _email(raw: str) -> str:
    e = raw.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e):
        raise HTTPException(400, "Enter a valid email address")
    return e


def _user_dict(u: AeroUser) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email}


def _start_session(response: Response, session: Session, user: AeroUser) -> None:
    token = new_token()
    session.add(SessionToken(token_hash=hash_token(token), subject_type="USER", subject_id=user.id, expires_at=now() + TTL))
    session.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=int(TTL.total_seconds()), path="/")


def ensure_demo_user() -> None:
    """A ready-made account so judges and teammates can sign in immediately. Disable with AEROSCOUT_DEMO_USER=0."""
    if os.environ.get("AEROSCOUT_DEMO_USER", "1") != "1":
        return
    with Session(engine) as s:
        if not s.exec(select(AeroUser).where(AeroUser.email == DEMO_EMAIL)).first():
            salt = new_salt()
            s.add(AeroUser(id="USR-DEMO", email=DEMO_EMAIL, name="Demo scout", salt=salt, pw_hash=hash_pin(DEMO_PASSWORD, salt)))
            s.commit()


def current_user(request: Request, session: Session = Depends(get_session)) -> AeroUser:
    token = request.cookies.get(COOKIE)
    st = session.get(SessionToken, hash_token(token)) if token else None
    if not st or st.subject_type != "USER" or expired(st.expires_at):
        raise HTTPException(401, "Sign in to continue")
    user = session.get(AeroUser, st.subject_id)
    if not user:
        raise HTTPException(401, "Sign in to continue")
    return user


@auth_router.post("/register")
def register(body: Registration, response: Response, session: Session = Depends(get_session)):
    email, name = _email(body.email), body.name.strip()
    if not name:
        raise HTTPException(400, "Enter your name")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if session.exec(select(AeroUser).where(AeroUser.email == email)).first():
        raise HTTPException(409, "An account with that email already exists. Sign in instead.")
    salt = new_salt()
    user = AeroUser(id="USR-" + uuid.uuid4().hex[:8].upper(), email=email, name=name[:80], salt=salt, pw_hash=hash_pin(body.password, salt))
    session.add(user); session.commit(); session.refresh(user)
    _start_session(response, session, user)
    return _user_dict(user)


@auth_router.post("/login")
def login(body: Credentials, response: Response, session: Session = Depends(get_session)):
    email = _email(body.email)
    recent = [t for t in _fails.get(email, []) if time.time() - t < 600]
    if len(recent) >= 5:
        raise HTTPException(429, "Too many attempts. Wait a few minutes and try again.")
    user = session.exec(select(AeroUser).where(AeroUser.email == email)).first()
    ok = bool(user) and hmac.compare_digest(hash_pin(body.password, user.salt), user.pw_hash)  # type: ignore[union-attr]
    if not ok:
        _fails[email] = recent + [time.time()]
        raise HTTPException(401, "Wrong email or password")
    _fails.pop(email, None)
    _start_session(response, session, user)  # type: ignore[arg-type]
    return _user_dict(user)  # type: ignore[arg-type]


@auth_router.get("/me")
def me(user: AeroUser = Depends(current_user)):
    return _user_dict(user)


@auth_router.post("/logout")
def logout(request: Request, response: Response, session: Session = Depends(get_session)):
    token = request.cookies.get(COOKIE)
    st = session.get(SessionToken, hash_token(token)) if token else None
    if st:
        session.delete(st); session.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
