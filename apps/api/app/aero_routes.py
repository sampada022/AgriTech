"""Public AeroScout API used by the website (/api/aeroscout/*). No login: this is a local demo, not a multi-tenant service."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlmodel import Session, select

from . import aeroscout
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from .aero_auth import current_user
from .aero_models import AeroScan, HotspotState, LeafPhoto
from .db import DB_FILE, LEAF_PHOTOS, SAMPLES, SCANS, UPLOADS, get_session

aero_router = APIRouter(prefix="/api/aeroscout", tags=["aeroscout"], dependencies=[Depends(current_user)])  # every AeroScout route needs a signed-in user
MAX_BYTES = 30 * 1024 * 1024
EXT = {".jpg", ".jpeg", ".png"}
SPECIES = ["Fall armyworm", "Stem borer", "Brown planthopper", "Leaf folder", "Aphids", "Other pest", "No pest found", "Not sure"]
STATES = ["new", "visited", "treated", "dismissed"]
NOT_A_PEST = ("Not sure", "No pest found")
FILES = {"image": "image.jpg", "overlay": "overlay.jpg", "vari": "vari.png", "texture": "texture.png"}


def _save_upload(up: UploadFile, dest_dir: Path, stem: str) -> Path:
    ext = Path(up.filename or "").suffix.lower()
    if ext not in EXT:
        raise HTTPException(400, "Upload a .jpg or .png photo")
    dest = dest_dir / f"{stem}{ext}"
    size = 0
    with dest.open("wb") as f:
        while chunk := up.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                f.close(); dest.unlink(missing_ok=True)
                raise HTTPException(413, "File is larger than 30 MB")
            f.write(chunk)
    try:
        with Image.open(dest) as im:
            im.verify()
    except (UnidentifiedImageError, OSError):
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "That file is not a readable image")
    return dest


def _scan_dict(s: AeroScan, photos: list[LeafPhoto] | None = None, states: list[HotspotState] | None = None) -> dict:
    r = s.result or {}
    st = {x.hotspot_id: x for x in states or []}
    by_hs: dict[str, list[LeafPhoto]] = {}
    for p in photos or []:
        by_hs.setdefault(p.hotspot_id, []).append(p)
    hs = []
    for h in r.get("hotspots", []):
        ph = by_hs.get(h["id"], [])
        confirmed = [p for p in ph if p.species not in ("Not sure",)]
        status = "Awaiting photo" if not ph else (f"Confirmed: {confirmed[-1].species}" if confirmed else "Photo received, species unsure")
        hs.append({**h, "status": status, "state": st[h["id"]].state if h["id"] in st else "new", "state_note": st[h["id"]].note if h["id"] in st else "",
                   "state_updated": st[h["id"]].updated_at.isoformat() if h["id"] in st else None, "photos": [{"id": p.id, "species": p.species, "note": p.note, "created_at": p.created_at.isoformat(),
                                                        "url": f"/api/aeroscout/leaf-photos/{p.id}/file"} for p in ph]})
    return {"id": s.id, "name": s.name, "source": s.source, "original_name": s.original_name, "status": s.status, "created_at": s.created_at.isoformat(),
            "gsd_cm": s.gsd_cm, "error": s.error, **{k: v for k, v in r.items() if k != "hotspots"}, "hotspots": hs,
            "files": {k: f"/api/aeroscout/scans/{s.id}/files/{k}" for k in FILES}}


def _full(session: Session, s: AeroScan) -> dict:
    return _scan_dict(s, session.exec(select(LeafPhoto).where(LeafPhoto.scan_id == s.id)).all(), session.exec(select(HotspotState).where(HotspotState.scan_id == s.id)).all())


def _get(session: Session, scan_id: str) -> AeroScan:
    s = session.get(AeroScan, scan_id)
    if not s:
        raise HTTPException(404, "Scan not found")
    return s


@aero_router.get("/samples")
def samples():
    return [{"name": p.name, "url": f"/api/aeroscout/samples/{p.name}", "kb": round(p.stat().st_size / 1024)}
            for p in sorted(SAMPLES.iterdir()) if p.suffix.lower() in EXT]


@aero_router.get("/samples/{name}")
def sample_file(name: str):
    p = (SAMPLES / name).resolve()
    if p.parent != SAMPLES.resolve() or not p.is_file():
        raise HTTPException(404, "No such sample")
    return FileResponse(p)


@aero_router.post("/scans")
def create_scan(file: UploadFile | None = File(None), sample: str | None = Form(None), name: str = Form(""), gsd_cm: float = Form(1.0),
                start: str = Form("bottom-left"), session: Session = Depends(get_session)):
    if not 0.05 <= gsd_cm <= 50:
        raise HTTPException(400, "gsd_cm should be between 0.05 and 50 (centimetres per pixel)")
    sid = "SCN-" + uuid.uuid4().hex[:8].upper()
    if sample:
        src = (SAMPLES / sample).resolve()
        if src.parent != SAMPLES.resolve() or not src.is_file():
            raise HTTPException(404, "No such sample")
        source, original = "sample", sample
    elif file is not None:
        src = _save_upload(file, UPLOADS, sid)
        source, original = "upload", file.filename or ""
    else:
        raise HTTPException(400, "Send a file or choose a sample")
    scan = AeroScan(id=sid, name=name.strip() or Path(original).stem or sid, source=source, original_name=original, gsd_cm=gsd_cm)
    try:
        scan.result = aeroscout.analyze(src, SCANS / sid, gsd_cm=gsd_cm, start=start)
    except Exception as e:  # keep the failure visible in the data console instead of a bare 500
        scan.status, scan.error = "FAILED", f"{type(e).__name__}: {e}"
    session.add(scan); session.commit(); session.refresh(scan)
    if scan.status == "FAILED":
        raise HTTPException(422, scan.error)
    return _full(session, scan)


@aero_router.get("/scans")
def list_scans(session: Session = Depends(get_session)):
    out = []
    for s in session.exec(select(AeroScan).order_by(AeroScan.created_at.desc())).all():
        d = _full(session, s)
        hs = d.get("hotspots", [])
        out.append({k: d[k] for k in ("id", "name", "source", "original_name", "status", "created_at", "gsd_cm", "error", "files")}
                   | {"hotspots": len(hs), "photos": sum(len(h["photos"]) for h in hs), "route_m": (d.get("route") or {}).get("distance_m"),
                      "field": d.get("field"), "severity": {k: sum(1 for h in hs if h["severity"] == k) for k in ("High", "Medium", "Low")},
                      "open": sum(1 for h in hs if h["state"] in ("new", "visited")), "area_m2": round(sum(h["area_m2"] for h in hs), 1)})
    return out


@aero_router.get("/scans/{scan_id}")
def get_scan(scan_id: str, session: Session = Depends(get_session)):
    return _full(session, _get(session, scan_id))


@aero_router.delete("/scans/{scan_id}")
def delete_scan(scan_id: str, session: Session = Depends(get_session)):
    s = _get(session, scan_id)
    for p in session.exec(select(LeafPhoto).where(LeafPhoto.scan_id == scan_id)).all():
        (LEAF_PHOTOS / p.filename).unlink(missing_ok=True); session.delete(p)
    for x in session.exec(select(HotspotState).where(HotspotState.scan_id == scan_id)).all():
        session.delete(x)
    shutil.rmtree(SCANS / scan_id, ignore_errors=True)
    for f in UPLOADS.glob(f"{scan_id}.*"):
        f.unlink(missing_ok=True)
    session.delete(s); session.commit()
    return {"ok": True}


@aero_router.get("/scans/{scan_id}/files/{kind}")
def scan_file(scan_id: str, kind: str):
    if kind not in FILES:
        raise HTTPException(404, "Unknown file")
    p = SCANS / scan_id / FILES[kind]
    if not p.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(p)


@aero_router.get("/species")
def species():
    return SPECIES


@aero_router.post("/scans/{scan_id}/hotspots/{hotspot_id}/photo")
def add_leaf_photo(scan_id: str, hotspot_id: str, file: UploadFile = File(...), species: str = Form("Not sure"), note: str = Form(""),
                   session: Session = Depends(get_session)):
    s = _get(session, scan_id)
    h = next((h for h in (s.result or {}).get("hotspots", []) if h["id"] == hotspot_id), None)
    if not h:
        raise HTTPException(404, "No such hotspot")
    if species not in SPECIES:
        raise HTTPException(400, "Unknown species option")
    pid = "LF-" + uuid.uuid4().hex[:8].upper()
    p = _save_upload(file, LEAF_PHOTOS, pid)
    row = LeafPhoto(id=pid, scan_id=scan_id, hotspot_id=hotspot_id, filename=p.name, species=species, note=note[:500],
                    tile_features={k: h[k] for k in ("vari", "vari_drop", "glcm_contrast", "glcm_entropy", "texture_ratio", "area_pct")})
    session.add(row); session.commit()
    return _full(session, s)


@aero_router.get("/leaf-photos/{photo_id}/file")
def leaf_file(photo_id: str, session: Session = Depends(get_session)):
    row = session.get(LeafPhoto, photo_id)
    if not row:
        raise HTTPException(404, "Photo not found")
    return FileResponse(LEAF_PHOTOS / row.filename)


@aero_router.get("/data")
def data_overview(session: Session = Depends(get_session)):
    """Everything the Data console shows: where files live, row counts, and the labelled examples collected so far."""
    scans = session.exec(select(AeroScan)).all()
    photos = session.exec(select(LeafPhoto)).all()
    return {
        "paths": {"database": str(DB_FILE), "samples": str(SAMPLES), "uploads": str(UPLOADS), "scan_outputs": str(SCANS), "leaf_photos": str(LEAF_PHOTOS)},
        "counts": {"scans": len(scans), "hotspots": sum(len((s.result or {}).get("hotspots", [])) for s in scans), "leaf_photos": len(photos),
                   "labelled_examples": sum(1 for p in photos if p.species != "Not sure")},
        "labelled_examples": [{"photo_id": p.id, "scan_id": p.scan_id, "hotspot": p.hotspot_id, "label": p.species, "features": p.tile_features,
                               "created_at": p.created_at.isoformat()} for p in photos],
        "note": "Labelled examples are stored for retraining. The detector does not retrain automatically in this build.",
    }


class StateBody(BaseModel):
    state: str
    note: str = ""


class RenameBody(BaseModel):
    name: str


@aero_router.patch("/scans/{scan_id}")
def rename_scan(scan_id: str, body: RenameBody, session: Session = Depends(get_session)):
    s = _get(session, scan_id)
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    s.name = name[:80]; session.add(s); session.commit()
    return _full(session, s)


@aero_router.patch("/scans/{scan_id}/hotspots/{hotspot_id}/state")
def set_state(scan_id: str, hotspot_id: str, body: StateBody, session: Session = Depends(get_session)):
    s = _get(session, scan_id)
    if not any(h["id"] == hotspot_id for h in (s.result or {}).get("hotspots", [])):
        raise HTTPException(404, "No such hotspot")
    if body.state not in STATES:
        raise HTTPException(400, f"state must be one of {STATES}")
    row = session.exec(select(HotspotState).where(HotspotState.scan_id == scan_id, HotspotState.hotspot_id == hotspot_id)).first() or HotspotState(scan_id=scan_id, hotspot_id=hotspot_id)
    row.state, row.note, row.updated_at = body.state, body.note[:500], datetime.now(timezone.utc)
    session.add(row); session.commit()
    return _full(session, s)


@aero_router.get("/scans/{scan_id}/export.csv")
def export_csv(scan_id: str, session: Session = Depends(get_session)):
    import csv, io
    from fastapi.responses import Response
    d = _full(session, _get(session, scan_id))
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["scan_id", "scan_name", "hotspot", "route_stop", "severity", "area_m2", "area_pct", "vari", "vari_drop", "glcm_contrast", "glcm_entropy", "state", "status", "species", "centre_x_pct", "centre_y_pct"])
    for h in d["hotspots"]:
        sp = "; ".join(p["species"] for p in h["photos"])
        w.writerow([d["id"], d["name"], h["id"], h.get("route_stop"), h["severity"], h["area_m2"], h["area_pct"], h["vari"], h["vari_drop"], h["glcm_contrast"], h["glcm_entropy"], h["state"], h["status"], sp, h["pct"][0], h["pct"][1]])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{d["id"]}-hotspots.csv"'})


@aero_router.get("/stats")
def stats(session: Session = Depends(get_session)):
    """Everything the dashboard overview and insights need, computed in one pass."""
    scans = session.exec(select(AeroScan).where(AeroScan.status == "COMPLETED").order_by(AeroScan.created_at.desc())).all()
    full = [_full(session, s) for s in scans]
    now = datetime.now(timezone.utc)
    days = [(now - timedelta(days=i)).date() for i in range(13, -1, -1)]
    by_day = {d: {"date": d.isoformat(), "scans": 0, "hotspots": 0} for d in days}
    species: dict[str, int] = {}
    severity = {"High": 0, "Medium": 0, "Low": 0}
    states = {k: 0 for k in STATES}
    queue, points, per_scan, activity = [], [], [], []
    area = route = photos_n = confirmed = awaiting = 0
    for d in full:
        created = datetime.fromisoformat(d["created_at"])
        if created.date() in by_day:
            by_day[created.date()]["scans"] += 1; by_day[created.date()]["hotspots"] += len(d["hotspots"])
        route += d["route"]["distance_m"] if d["hotspots"] else 0
        per_scan.append({"id": d["id"], "name": d["name"], "biotic_tiles": d["field"]["biotic_tiles"], "abiotic_tiles": d["field"]["abiotic_tiles"], "hotspots": len(d["hotspots"])})
        activity.append({"t": d["created_at"], "kind": "scan", "scan_id": d["id"], "text": f'Scan “{d["name"]}” analysed: {len(d["hotspots"])} hotspot{"" if len(d["hotspots"]) == 1 else "s"}'})
        for h in d["hotspots"]:
            area += h["area_m2"]; severity[h["severity"]] += 1; states[h["state"]] += 1
            ph = h["photos"]; photos_n += len(ph)
            conf = [p for p in ph if p["species"] not in NOT_A_PEST]
            if conf: confirmed += 1
            if not ph: awaiting += 1
            for p in ph:
                species[p["species"]] = species.get(p["species"], 0) + 1
                activity.append({"t": p["created_at"], "kind": "photo", "scan_id": d["id"], "text": f'Leaf photo for hotspot {h["id"]} in “{d["name"]}”: {p["species"]}'})
            if h["state_updated"]:
                activity.append({"t": h["state_updated"], "kind": "state", "scan_id": d["id"], "text": f'Hotspot {h["id"]} in “{d["name"]}” marked {h["state"]}'})
            points.append({"scan_id": d["id"], "scan_name": d["name"], "hotspot": h["id"], "vari_drop": h["vari_drop"], "glcm_contrast": h["glcm_contrast"],
                           "severity": h["severity"], "confirmed": bool(conf), "label": conf[-1]["species"] if conf else None})
            if h["state"] in ("new", "visited"):
                queue.append({"scan_id": d["id"], "scan_name": d["name"], "hotspot": h["id"], "severity": h["severity"], "area_m2": h["area_m2"], "state": h["state"],
                              "status": h["status"], "route_stop": h.get("route_stop"), "score": h["score"]})
    order = {"High": 0, "Medium": 1, "Low": 2}
    queue.sort(key=lambda q: (order[q["severity"]], -q["score"]))
    activity.sort(key=lambda a: a["t"], reverse=True)
    return {
        "totals": {"scans": len(full), "hotspots": sum(severity.values()), "area_m2": round(area, 1), "route_m": round(route, 1), "photos": photos_n,
                   "confirmed": confirmed, "awaiting_photo": awaiting, "open": len(queue)},
        "by_day": list(by_day.values()), "species": sorted(({"name": k, "count": v} for k, v in species.items()), key=lambda x: -x["count"]),
        "severity": severity, "states": states, "queue": queue, "points": points, "per_scan": per_scan, "activity": activity[:12],
        "latest_scan_id": full[0]["id"] if full else None,
    }
