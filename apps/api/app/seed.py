"""Seed demo farmers/operators and a first survey each, from the shipped sample images.

  uv run python -m app.seed

All people, phone numbers and PINs here are fictional demo data.
"""
from __future__ import annotations

import time

from sqlmodel import Session, select

from . import ingest
from . import security as sec
from .config import get_settings
from .db import create_tables, engine
from .models import SCAN_DONE, SCAN_FAILED, Farm, Farmer, Operator, Scan

DEMO_PIN = "1234"

FARMERS = [
    Farmer(id="MDY-001", name="Ramesh Gowda", village="Kikkeri, Mandya", language="kn",
           mobile="9000000001", access_mode="BOTH", collection_point="ಕೃಷಿ ಸೇವಾ ಕೇಂದ್ರ, ಕಿಕ್ಕೇರಿ"),
    Farmer(id="MDY-002", name="Lakshmamma", village="Maddur, Mandya", language="kn",
           mobile="9000000002", access_mode="ASSISTED", collection_point="ಮದ್ದೂರು FPO ಕಚೇರಿ"),
    Farmer(id="MDY-003", name="Suresh Kumar", village="Pandavapura, Mandya", language="en",
           mobile="9000000003", access_mode="DIGITAL", collection_point=""),
]
FARMS = [
    Farm(id="FARM-001", farmer_id="MDY-001", name="Kikkeri Paddy Plot A"),
    Farm(id="FARM-002", farmer_id="MDY-002", name="Maddur Paddy Plot"),
    Farm(id="FARM-003", farmer_id="MDY-003", name="Public-dataset maize plot (stand-in imagery)", crop="Maize"),
]
OPERATORS = [("OP-KIK", "Savitha", "Kikkeri Agri Service Centre"), ("OP-MAD", "Manjunath", "Maddur FPO Office")]
RUN_MAP = {
    "FARM-001": "stressed-paddy.png",
    "FARM-002": "healthy-paddy.png",
    "FARM-003": "demo-field-synthetic.jpg",
}


def main() -> None:
    create_tables()
    queued: list[tuple[str, str]] = []
    with Session(engine) as s:
        for obj in [*FARMERS, *FARMS]:
            s.merge(obj)
        for oid, name, centre in OPERATORS:
            salt = sec.new_salt()
            s.merge(Operator(id=oid, name=name, centre=centre, pin_salt=salt, pin_hash=sec.hash_pin(DEMO_PIN, salt)))
        s.commit()
        samples_dir = get_settings().data_dir / "samples"
        for farm_id, sample in RUN_MAP.items():
            path = samples_dir / sample
            if not path.exists():
                print(f"skip {farm_id}: sample {sample} not found under {samples_dir}")
                continue
            if s.exec(select(Scan).where(Scan.field_id == farm_id)).first():
                print(f"skip {farm_id}: already seeded")
                continue
            scan = ingest.start_survey(s, farm_id, path, gsd_cm=3.0, data_source="stand_in")
            queued.append((farm_id, scan.id))

    # create_scan() queues each on the engine's background worker; wait here so the PDF
    # report can be built before this script exits.
    with Session(engine) as s:
        for farm_id, scan_id in queued:
            scan = None
            for _ in range(120):
                s.expire_all()
                scan = s.get(Scan, scan_id)
                if scan.status in (SCAN_DONE, SCAN_FAILED):
                    break
                time.sleep(0.5)
            if scan and scan.status == SCAN_DONE:
                ingest.ensure_report(s, scan)
            print(f"seeded {farm_id} -> {scan_id} ({scan.status if scan else 'unknown'})")

    print("operators: OP-KIK / OP-MAD, PIN", DEMO_PIN, "| farmers: MDY-001, MDY-002 (assisted), MDY-003")


if __name__ == "__main__":
    main()
