from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from . import ingest, security as sec, simulation
from .config import get_settings
from .db import get_session
from .deps import DEMO_MODE, actor, current_farmer, current_operator, require_admin
from .diagnosis.guidance import LABELS
from .models import (
    SCAN_DONE, AccessLog, AccessRequest, Farm, Farmer, FieldRecord, Hotspot, LoginChallenge,
    Observation, Operator, Report, Scan, SessionToken, SmsMessage, new_id, now,
)
from .services.model import confirm_observation
from .services.serialize import iso
from .services.serialize import latest_scan as _latest_scan
from .sms import notify_text, otp_text, provider
from .storage import public_dir

def _samples_dir():
    return get_settings().data_dir / "samples"
LEGACY_VERDICT_MAP = {"PEST": "pest", "NOT_PEST": "false_alarm", "OTHER": "weeds_other"}


def _bad_code() -> HTTPException:
    return HTTPException(400, "Invalid or expired code")


# ---------------------------------------------------------------- helpers
def _issue_session(session: Session, kind: str, subject_id: str) -> dict:
    token = sec.new_token()
    exp = now() + sec.SESSION_TTL
    session.add(SessionToken(token_hash=sec.hash_token(token), subject_type=kind, subject_id=subject_id, expires_at=exp))
    session.commit()
    return {"token": token, "expires_at": exp.isoformat()}


def _hotspot_dict(h: Hotspot) -> dict:
    return {
        "id": h.id, "tier": h.tier, "biotic_score": round(h.biotic_score, 3),
        "hotspot_class": h.hotspot_class, "confidence": h.confidence, "area_m2": round(h.area_m2, 1),
        "cues": h.cues, "contributions": h.contributions, "abiotic_hint": h.abiotic_hint,
        "status": h.status, "label": h.label, "note": h.note, "rank": h.rank,
        "centroid": [h.centroid_lon, h.centroid_lat], "geometry": h.polygon,
    }


def _scan_payload(session: Session, scan: Scan, field: FieldRecord, farm: Farm) -> dict:
    hs = session.exec(select(Hotspot).where(Hotspot.scan_id == scan.id).order_by(Hotspot.rank)).all()
    rep = session.exec(select(Report).where(Report.scan_id == scan.id).order_by(Report.version.desc())).first()
    kpis = scan.kpis or {}
    return {
        "id": scan.id, "farm": {"id": farm.id, "name": farm.name, "crop": farm.crop},
        "status": scan.status, "created_at": scan.created_at.isoformat(), "data_source": field.data_source,
        "summary": {
            "valid_crop_area_sqm": kpis.get("field_area_m2"),
            "hotspots_detected": len(hs),
            "suspicious_area_sqm": kpis.get("area_flagged_m2"),
            "suspicious_area_percent": kpis.get("area_flagged_pct"),
            "status": "no_significant_anomaly" if not hs else "anomalies_detected",
        },
        "image": {
            "width_px": field.image_width, "height_px": field.image_height, "gsd_m": field.gsd_cm / 100,
            "bounds_wgs84": [field.sw_lat, field.sw_lon, field.ne_lat, field.ne_lon],
        },
        "kpis": kpis, "quality": scan.quality,
        "layers": sorted((scan.layers or {}).keys()),
        "hotspots": [_hotspot_dict(h) for h in hs], "report_id": rep.id if rep else None,
    }


def _own_scan(session: Session, farmer: Farmer, scan_id: str) -> tuple[Scan, FieldRecord, Farm]:
    s = session.get(Scan, scan_id)
    field = session.get(FieldRecord, s.field_id) if s else None
    farm = session.get(Farm, field.id) if field else None  # FieldRecord.id == Farm.id
    if not s or not farm or farm.farmer_id != farmer.id:
        raise HTTPException(404, "Survey not found")
    return s, field, farm


def _log(session: Session, report: Report, actor_type: str, actor_id: str, access_type: str, auth_id: str) -> None:
    session.add(AccessLog(farmer_id=report.farmer_id, report_id=report.id, actor_type=actor_type,
                          actor_id=actor_id, access_type=access_type, authorization_id=auth_id))
    session.commit()


# ---------------------------------------------------------------- farmer (digital) portal
farmer_router = APIRouter(prefix="/api/farmer", tags=["farmer"])


class LoginRequest(BaseModel):
    farmer_id: str


class LoginVerify(BaseModel):
    challenge_id: str
    otp: str


@farmer_router.post("/login/request")
def farmer_login_request(body: LoginRequest, session: Session = Depends(get_session)):
    farmer = session.get(Farmer, body.farmer_id.strip().upper())
    cid = sec.new_token()[:16]
    if farmer:
        recent = session.exec(select(LoginChallenge).where(
            LoginChallenge.farmer_id == farmer.id,
            LoginChallenge.expires_at > now() - sec.OTP_WINDOW + sec.OTP_TTL)).all()
        if len(recent) >= sec.OTP_REQUESTS_PER_WINDOW:
            raise HTTPException(429, "Too many code requests. Try again later.")
        otp = sec.new_otp()
        session.add(LoginChallenge(id=cid, farmer_id=farmer.id, otp_hash=sec.hash_otp(otp, cid),
                                   expires_at=now() + sec.OTP_TTL))
        session.commit()
        provider.send(session, farmer.mobile, otp_text(otp, "login"), "OTP")
    # Same response whether or not the farmer exists (no ID enumeration).
    return {"challenge_id": cid, "expires_in_s": int(sec.OTP_TTL.total_seconds())}


@farmer_router.post("/login/verify")
def farmer_login_verify(body: LoginVerify, session: Session = Depends(get_session)):
    ch = session.get(LoginChallenge, body.challenge_id)
    if not ch or ch.status != "PENDING":
        raise _bad_code()
    if sec.expired(ch.expires_at):
        ch.status = "EXPIRED"; session.add(ch); session.commit()
        raise _bad_code()
    if not sec.check_otp(body.otp.strip(), ch.id, ch.otp_hash):
        ch.attempts += 1
        if ch.attempts >= sec.OTP_MAX_ATTEMPTS:
            ch.status = "LOCKED"
        session.add(ch); session.commit()
        raise _bad_code()
    ch.status = "VERIFIED"; session.add(ch); session.commit()
    return _issue_session(session, "FARMER", ch.farmer_id)


@farmer_router.get("/me")
def farmer_me(farmer: Farmer = Depends(current_farmer), session: Session = Depends(get_session)):
    farms = session.exec(select(Farm).where(Farm.farmer_id == farmer.id)).all()
    out = []
    for f in farms:
        scans = session.exec(select(Scan).where(Scan.field_id == f.id).order_by(Scan.created_at.desc())).all()
        out.append({
            "id": f.id, "name": f.name, "crop": f.crop,
            "surveys": [
                {
                    "id": s.id, "status": "COMPLETED" if s.status == SCAN_DONE else s.status.upper(),
                    "created_at": s.created_at.isoformat(),
                    "summary": {"hotspots_detected": (s.kpis or {}).get("hotspot_count")},
                    "data_source": "real",
                }
                for s in scans
            ],
        })
    return {"id": farmer.id, "name": farmer.name, "village": farmer.village, "language": farmer.language, "farms": out}


@farmer_router.get("/surveys/{survey_id}")
def farmer_survey(survey_id: str, farmer: Farmer = Depends(current_farmer), session: Session = Depends(get_session)):
    scan, field, farm = _own_scan(session, farmer, survey_id)
    return _scan_payload(session, scan, field, farm)


@farmer_router.get("/surveys/{survey_id}/layers/{name}")
def farmer_layer(survey_id: str, name: str, farmer: Farmer = Depends(current_farmer), session: Session = Depends(get_session)):
    scan, _field, _farm = _own_scan(session, farmer, survey_id)
    info = (scan.layers or {}).get(name)
    if not info:
        raise HTTPException(404, "Layer not available")
    p = public_dir() / info["path"]
    if not p.exists():
        raise HTTPException(404, "Layer not available")
    return FileResponse(p, media_type=f"image/{info.get('format', 'webp')}")


@farmer_router.get("/surveys/{survey_id}/report")
def farmer_report(survey_id: str, download: bool = False, farmer: Farmer = Depends(current_farmer),
                  session: Session = Depends(get_session)):
    scan, _field, _farm = _own_scan(session, farmer, survey_id)
    rep = ingest.ensure_report(session, scan)
    if not rep or not Path(rep.path).exists():
        raise HTTPException(404, "Report not ready")
    _log(session, rep, "FARMER", farmer.id, "DOWNLOAD" if download else "VIEW", "SELF")
    return FileResponse(rep.path, media_type="application/pdf",
                        filename=f"{rep.id}.pdf" if download else None,
                        content_disposition_type="attachment" if download else "inline")


# ---------------------------------------------------------------- scout verdicts
verdict_router = APIRouter(prefix="/api/hotspots", tags=["verdict"])


class VerdictBody(BaseModel):
    verdict: str
    note: str = ""


@verdict_router.post("/{scan_id}/{hotspot_id}/verdict")
def set_verdict(scan_id: str, hotspot_id: str, body: VerdictBody, who: tuple[str, str] = Depends(actor),
                x_access_token: str | None = Header(None), session: Session = Depends(get_session)):
    label = LEGACY_VERDICT_MAP.get(body.verdict, body.verdict)
    if label not in LABELS:
        raise HTTPException(422, f"verdict must be one of {sorted(LEGACY_VERDICT_MAP) + list(LABELS)}")
    scan = session.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Survey not found")
    field = session.get(FieldRecord, scan.field_id)
    farm = session.get(Farm, field.id) if field else None
    kind, sid = who
    if kind == "FARMER":
        if not farm or farm.farmer_id != sid:
            raise HTTPException(404, "Survey not found")
    else:  # operators need the farmer's verified, unexpired authorization for this report
        rep = session.exec(select(Report).where(Report.scan_id == scan.id).order_by(Report.version.desc())).first()
        _authorize_access(session, sid, rep.id if rep else "", x_access_token)
    h = session.get(Hotspot, hotspot_id)
    if not h or h.scan_id != scan_id:
        raise HTTPException(404, "Hotspot not found")
    # A verdict with no photo still trains the model: a lightweight Observation carries the label.
    obs = Observation(id=new_id("o"), hotspot_id=hotspot_id, note=body.note[:500])
    session.add(obs)
    session.commit()
    confirm_observation(session, obs, label, body.note[:500])
    session.refresh(h)
    return _hotspot_dict(h)


# ---------------------------------------------------------------- assisted access (operator)
assisted_router = APIRouter(prefix="/api/assisted", tags=["assisted"])


class OperatorLogin(BaseModel):
    operator_id: str
    pin: str


class Lookup(BaseModel):
    farmer_id: str


class NewRequest(BaseModel):
    farmer_id: str
    report_id: str


class VerifyBody(BaseModel):
    otp: str


@assisted_router.post("/login")
def operator_login(body: OperatorLogin, session: Session = Depends(get_session)):
    op = session.get(Operator, body.operator_id.strip().upper())
    if not op or not sec.hmac.compare_digest(sec.hash_pin(body.pin, op.pin_salt), op.pin_hash):
        raise HTTPException(401, "Invalid operator ID or PIN")
    return {**_issue_session(session, "OPERATOR", op.id), "operator": {"id": op.id, "name": op.name, "centre": op.centre}}


@assisted_router.post("/lookup")
def lookup(body: Lookup, op: Operator = Depends(current_operator), session: Session = Depends(get_session)):
    f = session.get(Farmer, body.farmer_id.strip().upper())
    if not f or f.access_mode not in ("ASSISTED", "BOTH"):
        raise HTTPException(404, "No assisted-access farmer found with this ID")
    reps = session.exec(select(Report).where(Report.farmer_id == f.id).order_by(Report.generated_at.desc())).all()
    out, seen = [], set()
    for r in reps:
        if r.scan_id in seen:  # newest version per scan only
            continue
        seen.add(r.scan_id)
        scan = session.get(Scan, r.scan_id)
        out.append({"report_id": r.id, "survey_id": scan.id, "generated_at": r.generated_at.isoformat(),
                    "hotspots_detected": (scan.kpis or {}).get("hotspot_count")})
    return {"farmer_id": f.id, "name": f.name, "village": f.village, "language": f.language,
            "masked_mobile": sec.mask_mobile(f.mobile), "reports": out}


@assisted_router.post("/requests")
def create_request(body: NewRequest, op: Operator = Depends(current_operator), session: Session = Depends(get_session)):
    f = session.get(Farmer, body.farmer_id.strip().upper())
    rep = session.get(Report, body.report_id)
    if not f or not rep or rep.farmer_id != f.id or f.access_mode not in ("ASSISTED", "BOTH"):
        raise HTTPException(404, "Report not found for this farmer")
    recent = session.exec(select(AccessRequest).where(
        AccessRequest.farmer_id == f.id, AccessRequest.created_at > now() - sec.OTP_WINDOW)).all()
    if len(recent) >= sec.OTP_REQUESTS_PER_WINDOW:
        raise HTTPException(429, "Too many code requests for this farmer. Try again later.")
    rid = sec.new_token()[:16]
    otp = sec.new_otp()
    session.add(AccessRequest(id=rid, farmer_id=f.id, report_id=rep.id, operator_id=op.id,
                              otp_hash=sec.hash_otp(otp, rid), expires_at=now() + sec.OTP_TTL))
    session.commit()
    provider.send(session, f.mobile, otp_text(otp, "assisted", op.centre), "OTP")
    return {"request_id": rid, "masked_mobile": sec.mask_mobile(f.mobile),
            "expires_in_s": int(sec.OTP_TTL.total_seconds())}


@assisted_router.post("/requests/{request_id}/verify")
def verify_request(request_id: str, body: VerifyBody, op: Operator = Depends(current_operator),
                   session: Session = Depends(get_session)):
    r = session.get(AccessRequest, request_id)
    if not r or r.operator_id != op.id or r.status != "PENDING":
        raise _bad_code()
    if sec.expired(r.expires_at):
        r.status = "EXPIRED"; session.add(r); session.commit()
        raise _bad_code()
    if not sec.check_otp(body.otp.strip(), r.id, r.otp_hash):
        r.attempts += 1
        if r.attempts >= sec.OTP_MAX_ATTEMPTS:
            r.status = "LOCKED"
        session.add(r); session.commit()
        left = max(sec.OTP_MAX_ATTEMPTS - r.attempts, 0)
        raise HTTPException(400, f"Invalid or expired code. {left} attempt(s) left." if left else "Too many attempts. Request a new code.")
    token = sec.new_token()
    r.status, r.verified_at = "VERIFIED", now()  # OTP is single-use from here on
    r.access_token_hash, r.access_expires_at = sec.hash_token(token), now() + sec.ACCESS_TTL
    session.add(r); session.commit()
    return {"access_token": token, "report_id": r.report_id, "expires_at": r.access_expires_at.isoformat()}


def _authorize_access(session: Session, operator_id: str, report_id: str, token: str | None) -> AccessRequest:
    if not token:
        raise HTTPException(401, "Farmer authorization required")
    h = sec.hash_token(token)
    r = session.exec(select(AccessRequest).where(AccessRequest.access_token_hash == h)).first()
    if (not r or r.status != "VERIFIED" or r.operator_id != operator_id or r.report_id != report_id
            or not r.access_expires_at or sec.expired(r.access_expires_at)):
        raise HTTPException(401, "Authorization missing, expired or for a different report")
    return r


@assisted_router.get("/reports/{report_id}/summary")
def assisted_summary(report_id: str, op: Operator = Depends(current_operator),
                     x_access_token: str | None = Header(None), session: Session = Depends(get_session)):
    r = _authorize_access(session, op.id, report_id, x_access_token)
    rep = session.get(Report, report_id)
    _log(session, rep, "OPERATOR", op.id, "VIEW", r.id)
    scan = session.get(Scan, rep.scan_id)
    field = session.get(FieldRecord, scan.field_id)
    farm = session.get(Farm, field.id)
    return _scan_payload(session, scan, field, farm)


@assisted_router.get("/reports/{report_id}/download")
def assisted_download(report_id: str, op: Operator = Depends(current_operator),
                      x_access_token: str | None = Header(None), session: Session = Depends(get_session)):
    r = _authorize_access(session, op.id, report_id, x_access_token)
    rep = session.get(Report, report_id)
    if not Path(rep.path).exists():
        raise HTTPException(404, "Report file missing")
    _log(session, rep, "OPERATOR", op.id, "DOWNLOAD", r.id)
    return FileResponse(rep.path, media_type="application/pdf", filename=f"{rep.id}.pdf")


# ---------------------------------------------------------------- admin
admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class AnalysisBody(BaseModel):
    farm_id: str
    sample: str  # filename under data/samples, e.g. "stressed-paddy.png"
    gsd_cm: float = 3.0


@admin_router.post("/analyses")
def start_analysis(body: AnalysisBody, session: Session = Depends(get_session)):
    if not session.get(Farm, body.farm_id):
        raise HTTPException(404, "Unknown farm")
    path = _samples_dir() / body.sample
    if not path.is_file():
        raise HTTPException(400, f"No sample named {body.sample!r} under data/samples")
    scan = ingest.start_survey(session, body.farm_id, path, body.gsd_cm, data_source="stand_in")
    return {"survey_id": scan.id, "status": scan.status}


@admin_router.get("/surveys/{scan_id}")
def survey_status(scan_id: str, session: Session = Depends(get_session)):
    s = session.get(Scan, scan_id)
    if not s:
        raise HTTPException(404, "Unknown survey")
    return {"id": s.id, "status": s.status, "error": s.error}


@admin_router.post("/surveys/{scan_id}/notify")
def notify(scan_id: str, session: Session = Depends(get_session)):
    s = session.get(Scan, scan_id)
    if not s or s.status != SCAN_DONE:
        raise HTTPException(409, "Survey not completed")
    return ingest.notify_survey(session, s)


@admin_router.get("/sim/status")
def sim_status(session: Session = Depends(get_session)):
    return simulation.status(session)


@admin_router.post("/sim/start")
def sim_start(bg: BackgroundTasks, session: Session = Depends(get_session)):
    return simulation.start(session, bg)


@admin_router.post("/sim/reset")
def sim_reset(session: Session = Depends(get_session)):
    return simulation.reset(session)


@admin_router.get("/surveys/{scan_id}/layers/{name}")
def admin_layer(scan_id: str, name: str, session: Session = Depends(get_session)):
    s = session.get(Scan, scan_id)
    info = (s.layers or {}).get(name) if s else None
    if not info:
        raise HTTPException(404, "Layer not available")
    p = public_dir() / info["path"]
    if not p.exists():
        raise HTTPException(404, "Layer not available")
    return FileResponse(p, media_type=f"image/{info.get('format', 'webp')}")


@admin_router.get("/reports/{report_id}")
def admin_report(report_id: str, download: bool = False, session: Session = Depends(get_session)):
    rep = session.get(Report, report_id)
    if not rep or not Path(rep.path).exists():
        raise HTTPException(404, "Report not found")
    _log(session, rep, "ADMIN", "admin-console", "DOWNLOAD" if download else "VIEW", "ADMIN_KEY")
    return FileResponse(rep.path, media_type="application/pdf", filename=f"{rep.id}.pdf" if download else None,
                        content_disposition_type="attachment" if download else "inline")


@admin_router.get("/overview")
def overview(session: Session = Depends(get_session)):
    rows = []
    for s in session.exec(select(Scan).order_by(Scan.created_at.desc())).all():
        field = session.get(FieldRecord, s.field_id)
        farm = session.get(Farm, field.id) if field else None
        if not farm:
            continue  # Studio demo/ad-hoc scans aren't tied to a farmer
        f = session.get(Farmer, farm.farmer_id)
        kpis = s.kpis or {}
        rows.append({"survey_id": s.id, "farm": farm.name, "farmer": f.name, "farmer_id": f.id, "village": f.village,
                     "status": s.status, "hotspots": kpis.get("hotspot_count"),
                     "suspicious_percent": kpis.get("area_flagged_pct"), "data_source": field.data_source})
    logs = session.exec(select(AccessLog).order_by(AccessLog.at.desc())).all()[:25]
    return {"surveys": rows, "access_log": [l.model_dump(mode="json") for l in logs]}


# ---------------------------------------------------------------- dev: SMS outbox (demo phone simulator)
dev_router = APIRouter(prefix="/api/dev", tags=["dev"])


@dev_router.get("/sms")
def dev_sms(mobile: str, session: Session = Depends(get_session)):
    if not DEMO_MODE:
        raise HTTPException(404, "Not found")
    msgs = session.exec(select(SmsMessage).where(SmsMessage.to_mobile == mobile).order_by(SmsMessage.pk.desc())).all()[:20]
    # SQLite drops the timezone on round-trip, so the raw dump below has no offset. JS's `new
    # Date(...)` treats an offset-less string as LOCAL time, not UTC -- stamping it wrong by
    # the viewer's UTC offset, which is why "just sent" polling on the landing-page demo never
    # found a message that had in fact just arrived. iso() makes the UTC explicit.
    return [{**m.model_dump(mode="json"), "at": iso(m.at)} for m in msgs]


# ---------------------------------------------------------------- dev: the website's "see it as a farmer" demo
# No login for this on purpose: it narrates the real product's farmer-facing surface (an SMS and a
# PDF, never a dashboard), so the site visitor plays the farmer's part without an account.
DEMO_FARM_ID = "FARM-001"


@dev_router.post("/demo/run")
def dev_demo_run(session: Session = Depends(get_session)):
    if not DEMO_MODE:
        raise HTTPException(404, "Not found")
    farm = session.get(Farm, DEMO_FARM_ID)
    farmer = session.get(Farmer, farm.farmer_id) if farm else None
    scan = _latest_scan(session, DEMO_FARM_ID) if farm else None
    if not farm or not farmer or not scan or scan.status != SCAN_DONE:
        raise HTTPException(409, "Demo field is not seeded yet. Run `python -m app.seed` first.")
    rep = ingest.ensure_report(session, scan)
    result = ingest.notify_survey(session, scan)
    return {
        "farmer_id": farmer.id, "farmer_name": farmer.name, "village": farmer.village,
        "mobile": farmer.mobile, "masked_mobile": sec.mask_mobile(farmer.mobile),
        "survey_id": scan.id, "report_id": rep.id if rep else None, "sent": result.get("sent", False),
    }


@dev_router.get("/demo/report/{report_id}")
def dev_demo_report(report_id: str, session: Session = Depends(get_session)):
    if not DEMO_MODE:
        raise HTTPException(404, "Not found")
    rep = session.get(Report, report_id)
    if not rep or not Path(rep.path).exists():
        raise HTTPException(404, "Report not found")
    return FileResponse(rep.path, media_type="application/pdf")
